# Agentic RAG Implementation Guide for CareFlow Medical Info Agent

> **Author:** Dr. Patrick Lewis (Meta AI Research, RAG co-author)
> **Reviewer role:** Validation of Agentic RAG implementation in `careflow/agents/medical_info/`
> **Date:** 2026-04-05
> **Scope:** Medical history retrieval over AlloyDB + pgvector, Gemini `text-embedding-004` (768-dim), ADK function tools.
> **Audience:** Senior engineers implementing and reviewing the Medical Info Agent.

---

## 0. TL;DR

CareFlow의 Medical Info Agent는 단순 top-k cosine search로는 부족합니다. 환자 안전(false-negative 최소화), 의료 용어 다양성(chest pain ↔ angina), 시간 민감성(최근 visit 우선)을 고려할 때 **Agentic RAG loop — Retrieve → Critique → Reformulate → Retrieve → Synthesize** 가 필수입니다.

A plain top-k cosine search is insufficient for the Medical Info Agent. Given patient-safety constraints (minimize false negatives), medical-term variability, and temporal sensitivity, an **Agentic RAG loop — Retrieve → Critique → Reformulate → Retrieve → Synthesize** is required.

Recommended pattern for 2026: **CRAG-style retrieval evaluator + HyDE query expansion + bounded self-critique loop (max 3 iterations) + keyword fallback**. Full Self-RAG token training is out of scope — we emulate the behavior via prompted critique instead.

---

## 1. State-of-the-Art Landscape (2023 → 2026)

### 1.1 Self-RAG (Asai et al., 2023)
- Trains a single LM to emit **reflection tokens**: `Retrieve`, `ISREL` (is-relevant), `ISSUP` (is-supported), `ISUSE` (utility).
- Retrieval becomes **adaptive on-demand** rather than mandatory every turn.
- Per-passage critique is generated *before* answer synthesis; the model can reject irrelevant retrieval.
- **CareFlow takeaway:** We do **not** train a new model. Instead, we emulate Self-RAG's `ISREL`/`ISSUP`/`ISUSE` semantics via a structured prompted critique step on Gemini 2.x (see §4.3).

### 1.2 HyDE — Hypothetical Document Embedding (Gao et al., 2022)
- Generate a hypothetical *answer* (fake document) from the raw query, embed **that**, retrieve neighbors.
- Narrows the query↔document semantic gap: patient questions are short and lay ("my sugar is high"), stored visit summaries are long and clinical ("HbA1c 7.5%, fasting glucose 145 mg/dL").
- The encoder's dense bottleneck filters hallucinations from the hypothetical document.
- **CareFlow takeaway:** HyDE is **high value** here because lay↔clinical vocabulary drift is exactly our problem. Apply HyDE on ambiguous or lay-language queries.

### 1.3 Corrective RAG — CRAG (Yan et al., 2024)
- Lightweight **retrieval evaluator** scores each retrieved passage into `{Correct, Incorrect, Ambiguous}`.
- `Correct` → decompose-then-recompose refinement.
- `Incorrect` → discard all, fall back to web search (or in our case: keyword search / broader query).
- `Ambiguous` → mix both.
- **CareFlow takeaway:** This is the **primary pattern** we implement. Thresholds:
  - `>= 0.78` cosine → Correct (strict, medical safety)
  - `< 0.55` cosine → Incorrect (reformulate + retry)
  - in between → Ambiguous (expand query, retry)

### 1.4 Multi-hop / Iterative RAG
- Multi-hop queries require 2+ retrieval rounds over different sub-intents. Example: *"Did my BP improve after the medication Dr. Patel started?"* → (1) retrieve Dr. Patel's visit → (2) extract medication name → (3) retrieve subsequent BP metrics.
- 2026 SOTA (e.g. Deep-DxSearch, Agentic Graph RAG): state-driven "retrieve-evaluate-refine" loop with RL-learned stop conditions.
- **CareFlow takeaway:** Implement a **bounded loop (max 3 iterations)** with deterministic stop conditions (§3.5). No RL training — use prompted critique.

### 1.5 Query Reformulation & Medical Synonyms
- UMLS-based expansion has shown ~42% of reformulated queries beat the original (Plovnick 2004). Net positive with careful gating.
- In 2026 LLM-era, we prefer **LLM-driven reformulation conditioned on a small domain synonym map** rather than heavyweight UMLS Metathesaurus lookups — lower latency, easier to audit, and Gemini 2.x already knows most clinical synonyms.

---

## 2. Why Agentic RAG for the Medical Domain

| Dimension | Plain Top-k RAG | Agentic RAG |
|---|---|---|
| False negatives | High (single query, single retrieval) | Low (critique + reformulate + retry) |
| Lay ↔ clinical gap | Poor | HyDE / synonym expansion closes it |
| Multi-hop clinical questions | Fails | Loop handles sub-intents |
| Temporal reasoning ("most recent") | Weak | Critique step enforces recency |
| Citation / auditability | Optional | **Mandatory** — every claim traces to a `visit_id` |
| Patient safety posture | Reactive | Proactive (conservative stop condition) |

**Core design principle for CareFlow:**
> **"When in doubt, retrieve again. When still in doubt, say so."**
> 모호하면 다시 검색하고, 그래도 모호하면 불확실함을 명시한다. 절대 hallucinate 하지 않는다.

---

## 3. Architecture for CareFlow Medical Info Agent

### 3.1 Component Diagram (logical)

```
user query
   │
   ▼
[ Query Analyzer ]  ── classify: simple | multi-hop | temporal | comparative
   │
   ▼
[ Query Rewriter ] ── apply medical synonym map + (optional) HyDE expansion
   │
   ▼
┌──────────────  AGENTIC LOOP (max 3 iters)  ───────────────┐
│                                                            │
│   [ Retriever ] ── pgvector cosine on visit_records         │
│        │                                                    │
│        ▼                                                    │
│   [ Retrieval Evaluator (CRAG-style) ]                      │
│        │       ┌─ Correct   → break                         │
│        │       ├─ Ambiguous → expand query, loop            │
│        │       └─ Incorrect → reformulate + loop            │
│        ▼                                                    │
│   [ Self-Critique ]                                         │
│        ── "Do these passages actually answer the question?" │
│        ── If NO and iters < max → loop with new sub-query   │
└────────────────────────────────────────────────────────────┘
   │
   ▼
[ Synthesizer ] ── generate answer with inline citations [VIS-001]
   │
   ▼
[ PII Filter ] ── strip any leaked identifiers before returning
```

### 3.2 Data Path
- **Embedding model:** `text-embedding-004` (Gemini), 768-dim, already wired in `tools.py::_generate_embedding`.
- **Store:** AlloyDB with pgvector `vector(768)` column on `visit_records.embedding`.
- **Index:** HNSW with `vector_cosine_ops`, `m=16, ef_construction=64` (create if not present).
- **Distance:** `1 - (a <=> b)` for cosine similarity in `[0, 1]`.

### 3.3 Retrieval SQL (reference)

```sql
SELECT
    id AS visit_id,
    visit_date,
    doctor_name,
    hospital_name,
    structured_summary,
    key_findings,
    1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
FROM visit_records
WHERE patient_id = :pid
  AND embedding IS NOT NULL
ORDER BY embedding <=> CAST(:qvec AS vector)
LIMIT :k;
```

> **Note:** `<=>` is pgvector's cosine distance operator. Recency bias should be applied *after* the ANN search as a re-rank, not inside the ORDER BY, to preserve index usage.

### 3.4 Re-ranking with Recency

```python
def rerank_with_recency(results, half_life_days=180):
    today = datetime.today().date()
    for r in results:
        age = (today - date.fromisoformat(r["visit_date"])).days
        decay = 0.5 ** (age / half_life_days)          # 6-month half-life
        r["final_score"] = 0.75 * r["similarity"] + 0.25 * decay
    return sorted(results, key=lambda x: x["final_score"], reverse=True)
```

### 3.5 Loop Termination Conditions (all must be enforceable)

1. **Hard cap:** `max_iterations = 3`.
2. **Success:** retrieval evaluator returns `Correct` AND self-critique returns `sufficient=True`.
3. **Saturation:** two consecutive iterations return the same top-k `visit_id` set → break.
4. **Empty-space:** reformulated query yields `results_count == 0` after fallback → break with `status="no_evidence"`.
5. **Budget:** total tokens spent on critique > 4000 → break (cost guard).

---

## 4. Implementation Guidance

### 4.1 Where this lives
- `careflow/agents/medical_info/tools.py` — existing file. Add new tool `search_medical_history_agentic` *alongside* (do not replace) `search_medical_history`. Keep the legacy tool as a deterministic fallback.
- `careflow/agents/medical_info/rag/` — new subpackage:
  - `query_rewriter.py` — synonym map + HyDE
  - `evaluator.py` — CRAG-style scoring
  - `critic.py` — prompted self-critique
  - `loop.py` — the orchestrator
- `careflow/agents/medical_info/prompt.py` — add critique/reformulation prompts.

### 4.2 Medical Synonym Map (seed list — extend as needed)

```python
MEDICAL_SYNONYMS = {
    # cardiovascular
    "chest pain": ["angina", "chest discomfort", "retrosternal pain"],
    "heart attack": ["myocardial infarction", "mi", "stemi", "nstemi"],
    "bp": ["blood pressure", "hypertension", "htn", "systolic", "diastolic"],
    "high bp": ["hypertension", "htn", "elevated blood pressure"],
    "irregular heartbeat": ["arrhythmia", "afib", "atrial fibrillation"],
    # endocrine
    "sugar": ["glucose", "blood sugar", "glycemia", "hba1c"],
    "diabetes": ["dm", "type 2 diabetes", "t2dm", "hyperglycemia"],
    "thyroid": ["tsh", "hypothyroid", "hyperthyroid", "t3", "t4"],
    # renal
    "kidney": ["renal", "nephro", "egfr", "creatinine"],
    # lipid
    "cholesterol": ["lipid", "ldl", "hdl", "triglycerides", "dyslipidemia"],
    # meds — common brand↔generic
    "tylenol": ["acetaminophen", "paracetamol"],
    "advil": ["ibuprofen", "nsaid"],
    "aspirin": ["asa", "acetylsalicylic acid"],
}
```

> Keep this **small, curated, auditable**. Do NOT try to encode UMLS inline. If the synonym map grows past ~200 entries, move it to a config file reviewed by a clinical SME.

### 4.3 Self-Critique Prompt (structured JSON output)

```
You are a clinical information retrieval critic. Evaluate whether the
retrieved visit records can answer the patient's question.

QUESTION: {query}
RETRIEVED PASSAGES:
{passages_with_ids}

Return STRICT JSON:
{
  "is_relevant": bool,        // Self-RAG ISREL
  "is_supported": bool,       // Self-RAG ISSUP — does evidence support a direct answer?
  "is_sufficient": bool,      // Self-RAG ISUSE — enough to answer without guessing?
  "missing_info": string,     // what is missing, if anything
  "suggested_subquery": string|null,  // for next hop, null if done
  "confidence": float         // 0.0–1.0
}

Rules:
- Prefer "is_sufficient=false" when uncertain. Patient safety > recall.
- If the question asks about trends/changes, you need ≥2 dated visits.
- If the question is time-specific ("last visit"), the top result MUST match.
```

### 4.4 HyDE Application (conditional, not always)

HyDE adds one LLM call per query — only trigger when it pays off:

```python
def should_use_hyde(query: str) -> bool:
    # Short, lay-language queries benefit most.
    if len(query.split()) > 15:          # long queries — already specific
        return False
    if any(t in query.lower() for t in ["hba1c", "egfr", "ldl", "mmhg"]):
        return False                      # already clinical
    return True
```

HyDE prompt:
```
Write a short (2-3 sentence) clinical visit note that would answer this
patient question. Use clinical terminology. Do NOT invent specific numbers.

Question: {query}
Clinical note:
```
Then embed the generated note (not the original query) and retrieve.

### 4.5 Reference Orchestrator Skeleton

```python
def agentic_medical_search(
    patient_id: str,
    query: str,
    tool_context: ToolContext,
    max_iterations: int = 3,
    top_k: int = 5,
) -> dict:
    trace = []                       # audit trail for citation
    seen_ids: set[str] = set()
    current_query = query
    final_results = []

    for iteration in range(max_iterations):
        # 1. Rewrite — synonyms + optional HyDE
        rewritten = rewrite_query(current_query)
        embed_input = hyde_expand(rewritten) if should_use_hyde(rewritten) else rewritten

        # 2. Embed + retrieve (with keyword fallback)
        qvec = _generate_embedding(embed_input)
        if qvec is None:
            results = _keyword_fallback(patient_id, rewritten, tool_context, top_k)
            trace.append({"iter": iteration, "mode": "keyword_fallback"})
        else:
            results = _pgvector_search(patient_id, qvec, top_k)
            trace.append({"iter": iteration, "mode": "vector", "query": rewritten})

        # 3. Recency re-rank
        results = rerank_with_recency(results)

        # 4. CRAG evaluator on similarity distribution
        verdict = crag_evaluate(results)   # Correct | Ambiguous | Incorrect

        # 5. Self-critique (prompted LLM)
        critique = self_critique(query, results)

        # 6. Merge new results into the running set (dedup by visit_id)
        for r in results:
            if r["visit_id"] not in seen_ids:
                seen_ids.add(r["visit_id"])
                final_results.append(r)

        # 7. Stop conditions
        if verdict == "Correct" and critique["is_sufficient"]:
            break
        if verdict == "Incorrect" and iteration == max_iterations - 1:
            break
        if not critique["suggested_subquery"]:
            break

        # 8. Reformulate for the next hop
        current_query = critique["suggested_subquery"]

    return {
        "status": "success" if final_results else "no_evidence",
        "query": query,
        "iterations": len(trace),
        "results_count": len(final_results),
        "results": final_results,
        "trace": trace,              # for auditability — Self-RAG-style
        "critique": critique,        # final ISREL/ISSUP/ISUSE verdict
    }
```

### 4.6 Citation / Source Attribution

Every fact returned to the synthesizer **must** carry a `visit_id`. The synthesizer prompt must require inline citations like `[VIS-002, 2026-03-15]`. Reject any model output that contains numerical clinical values without an adjacent citation.

```python
CITATION_REGEX = re.compile(r"\[VIS-\d{3},\s*\d{4}-\d{2}-\d{2}\]")

def validate_citations(answer: str, allowed_ids: set[str]) -> bool:
    cites = CITATION_REGEX.findall(answer)
    return bool(cites) and all(any(aid in c for aid in allowed_ids) for c in cites)
```

### 4.7 Keyword Fallback

Already half-implemented in `tools.py::_simple_keyword_match`. Promote it to a first-class branch in the orchestrator, triggered when:
- `_generate_embedding` returns `None` (network / quota failure), OR
- pgvector returns 0 rows, OR
- pgvector best similarity < 0.35 (definitely off-target).

Fallback must still go through the CRAG evaluator so the caller sees a uniform verdict.

---

## 5. Validation Checklist (reviewer-facing)

**Use this checklist when validating the other sub-agent's implementation. Each item must be a green check before merge.**

### 5.1 Embedding & Vector Search
- [ ] `_generate_embedding` is called with the **rewritten** query, not the raw user query.
- [ ] Model string is exactly `text-embedding-004` and vector length is asserted to be 768.
- [ ] Embedding failures return `None` and trigger the keyword fallback — **never** a silent empty result.
- [ ] pgvector query uses `CAST(:qvec AS vector)` binding, not string interpolation.
- [ ] SQL uses `ORDER BY embedding <=> :qvec` (cosine distance), not `<->` (L2).
- [ ] `patient_id` is always in the `WHERE` clause (cross-patient leakage = P0 bug).
- [ ] An HNSW index exists on `visit_records.embedding` with `vector_cosine_ops`.

### 5.2 Quality Evaluation (CRAG)
- [ ] Retrieval evaluator classifies into `Correct | Ambiguous | Incorrect`.
- [ ] Thresholds are constants (not magic numbers scattered in code): `CRAG_UPPER=0.78`, `CRAG_LOWER=0.55`.
- [ ] Thresholds are logged alongside every decision for later tuning.
- [ ] `Incorrect` verdict triggers reformulation, not a silent empty return.

### 5.3 Query Reformulation
- [ ] Reformulation is triggered by: (a) `Incorrect`/`Ambiguous` verdict, (b) `is_sufficient=false`, or (c) multi-hop sub-query.
- [ ] Medical synonym map is applied deterministically **before** the LLM reformulation (cheap step first).
- [ ] HyDE is gated by `should_use_hyde()` — not every query.
- [ ] Reformulated query is distinct from the previous iteration's query (string-equality check → abort loop).

### 5.4 Multi-hop / Iterative Retrieval
- [ ] Loop supports **at least 2 hops**, capped at **3 hops**.
- [ ] Results are deduplicated by `visit_id` across hops.
- [ ] Each hop's query, mode, top score, and verdict are recorded in a `trace` list.
- [ ] Loop cannot run forever: every termination condition from §3.5 is implemented.

### 5.5 Self-Critique
- [ ] Critique step returns structured JSON with `is_relevant`, `is_supported`, `is_sufficient`, `suggested_subquery`, `confidence`.
- [ ] JSON parse errors do **not** crash the loop — they are treated as `is_sufficient=false` and logged.
- [ ] Critic prompt instructs conservative bias ("prefer false when uncertain").
- [ ] Critic has access to the **original** user query, not just the rewritten one.

### 5.6 Medical Domain Handling
- [ ] Synonym map covers: BP/hypertension, chest pain/angina, sugar/glucose/HbA1c, kidney/eGFR, cholesterol/LDL.
- [ ] Brand↔generic drug mapping exists for at least the drugs already in mock data (Metformin, Amlodipine, Aspirin, Atorvastatin).
- [ ] Temporal keywords ("last visit", "recent", "latest", "since") trigger recency re-rank boost.
- [ ] Comparative queries ("improved", "changed", "worse") force ≥2 results before `is_sufficient=true`.

### 5.7 Citation & Attribution
- [ ] Every returned result carries `visit_id`, `visit_date`, `doctor_name`, `hospital_name`.
- [ ] Downstream synthesizer prompt mandates inline citations.
- [ ] `validate_citations()` is called before returning to the user.
- [ ] Responses with unsupported numerical claims are rejected or rewritten.

### 5.8 Fallback & Resilience
- [ ] Keyword fallback is reachable (integration-tested with mocked embedding failure).
- [ ] AlloyDB connection failure falls back to in-memory mock (already in `tools.py`).
- [ ] Fallback mode is surfaced in the response as `source: "keyword_fallback"` — never hidden.
- [ ] No code path can return `status="success"` with `results_count=0`.

### 5.9 Loop Safety
- [ ] `max_iterations` is a parameter, defaulting to 3.
- [ ] Token / cost budget guard is implemented.
- [ ] Same-result saturation is detected and breaks the loop.
- [ ] Unit test exists for each termination condition.

### 5.10 Privacy / PII
- [ ] No PII (phone, email, full name of caregivers) is placed into embedding text.
- [ ] Trace logs strip caregiver contact details before persistence.
- [ ] Any field going into Gemini embedding is length-capped (already 2000 chars in existing code — verify it still holds after refactor).
- [ ] Cross-patient result leakage has a **regression test** (query patient_A, assert no patient_B rows).

### 5.11 Observability
- [ ] Every loop iteration emits a structured log line: `{iter, query, mode, top_sim, verdict, sufficient}`.
- [ ] A `trace` field is returned in the tool response for the UI / audit.
- [ ] Latency per iteration is measured (target: < 800ms p95 per hop).

---

## 6. Medical-Domain Considerations (Deep Dive)

### 6.1 Patient Safety — Minimize False Negatives
A false negative in medical retrieval ("no, you never had chest pain") is far more dangerous than a false positive. Design implications:
- Prefer **recall over precision** in the retriever — cast a wider net (top_k=8–10), let the critique step prune.
- Conservative stop condition: `is_sufficient=false` by default. The critic must *affirmatively* mark sufficiency.
- When the loop terminates with low confidence, the synthesizer must say so explicitly: *"I don't find a clear record of this in your visits from the last 12 months. You may want to confirm with Dr. Sharma."*

### 6.2 Medical Jargon — Dual-direction Translation
- **Lay → Clinical:** "my sugar is high" → "hyperglycemia / HbA1c elevated" (for retrieval).
- **Clinical → Lay:** `HbA1c 7.5%` → "average blood sugar over the last 3 months was elevated" (for response). The retrieval side cares about the first direction; synthesis cares about the second.

### 6.3 Temporal Sensitivity
- Patient questions are almost always biased toward **recent** events ("what did the doctor say last time").
- Apply the recency re-rank in §3.4. 6-month half-life is a reasonable default — shorter for acute conditions, longer for chronic.
- For "trend" questions, explicitly widen the window and sort chronologically *after* filtering.

### 6.4 Privacy / PII Filtering
- `visit_records.structured_summary` may contain caregiver names, phone numbers, address fragments. **Never** embed raw PII-heavy text verbatim — pre-scrub before embedding.
- Output layer must strip PII from any fields that accidentally carry it.
- CareFlow already isolates caregiver data to `_MOCK_CAREGIVER` / `caregivers` table — keep it that way. Do not join caregiver PII into retrieval results unless the tool is explicitly `get_caregiver_info`.

### 6.5 Regulatory Posture (HIPAA-ish, even in the demo)
- Every retrieval decision should be **auditable**: which query, which vector, which passages, which verdict. The `trace` field in §4.5 is not optional — it is the audit artifact.
- `patient_id` filter is mandatory on every SQL statement touching patient data. This should be enforced by a single helper, not repeated manually.

---

## 7. What NOT to do

- Do **not** fine-tune a custom reflection-token model. We emulate Self-RAG via prompting.
- Do **not** use UMLS Metathesaurus inline — too heavy for the loop budget. Use a curated synonym map.
- Do **not** let the loop run unbounded. 3 hops max, full stop.
- Do **not** drop the legacy `search_medical_history` tool. Keep it as a deterministic fallback for when the agentic loop fails.
- Do **not** embed raw user input with PII. Scrub first.
- Do **not** return `status=success, results_count=0`. That is a lie. Use `status=no_evidence`.
- Do **not** hide fallback mode from the response — observability matters.

---

## 8. Acceptance Test Scenarios

Minimum test set the reviewer should run before approving:

1. **Simple lookup:** *"What was my last HbA1c?"* → 1 hop, `Correct`, cites VIS-001.
2. **Lay synonym:** *"Is my sugar getting better?"* → synonym expansion to "HbA1c/glucose", ≥2 visits retrieved, trend statement.
3. **Multi-hop:** *"Did my BP improve after Dr. Patel started me on the new medicine?"* → hop 1 (Dr. Patel visit, finds Amlodipine), hop 2 (subsequent BP metrics).
4. **Temporal:** *"What did Dr. Sharma say at my most recent visit?"* → recency re-rank picks VIS-001 over VIS-003 despite similar content.
5. **Not in history:** *"Have I ever had a stroke?"* → loop terminates with `no_evidence`, response explicitly says so.
6. **Embedding failure:** mock `_generate_embedding` → `None`. Assert keyword fallback path, `source="keyword_fallback"`.
7. **Cross-patient isolation:** query with `patient_id="patient_002"`. Assert zero rows from `patient_001`.
8. **Citation validation:** force the synthesizer to emit an uncited numeric claim. Assert `validate_citations()` rejects it.

---

## 9. References

Sources consulted (April 2026):

- [Self-RAG: Learning to Retrieve, Generate and Critique through Self-Reflection — Asai et al. 2023 (arXiv)](https://arxiv.org/abs/2310.11511)
- [Self-RAG project page](https://selfrag.github.io/)
- [Self-RAG official implementation (GitHub)](https://github.com/AkariAsai/self-rag)
- [Corrective Retrieval Augmented Generation — Yan et al. 2024 (arXiv)](https://arxiv.org/abs/2401.15884)
- [CRAG reference implementation (GitHub)](https://github.com/HuskyInSalt/CRAG)
- [CRAG with LangGraph tutorial — DataCamp](https://www.datacamp.com/tutorial/corrective-rag-crag)
- [Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) — Gao et al. 2022 (arXiv)](https://arxiv.org/abs/2212.10496)
- [HyDE in Haystack — deepset docs](https://docs.haystack.deepset.ai/docs/hypothetical-document-embeddings-hyde)
- [A self-correcting Agentic Graph RAG for clinical decision support in hepatology — Frontiers in Medicine 2025](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1716327/full)
- [Agentic RAG in Healthcare — Indium](https://www.indium.tech/blog/agentic-rag-in-healthcare/)
- [AgenticRAG-Survey (GitHub)](https://github.com/asinghcsu/AgenticRAG-Survey)
- [End-to-End Agentic RAG System Training for Traceable Diagnostic Reasoning (Deep-DxSearch) — arXiv 2508.15746](https://arxiv.org/pdf/2508.15746)
- [From Conflict to Consensus: Multi-Round Agentic RAG for Medical Reasoning — arXiv 2603.03292](https://arxiv.org/html/2603.03292v2)
- [A survey on RAG models for healthcare applications — Neural Computing and Applications 2025](https://link.springer.com/article/10.1007/s00521-025-11666-9)
- [Query specific graph-based query reformulation using UMLS — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1532046420301210)
- [The Next Frontier of RAG (2026-2030) — NStarX](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)

---

## 10. Sign-off

When all items in §5 are green and §8 scenarios pass, this validator will approve the Agentic RAG implementation for the CareFlow Medical Info Agent.

— **Dr. Patrick Lewis**, RAG validation lead
