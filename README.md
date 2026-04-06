# CareFlow Agents

Multi-agent healthcare post-visit care coordination system built on Google ADK.

> Part of **CareFlow** — Google Cloud Gen AI Academy APAC Edition, Cohort 1 Hackathon.

---

## What this repo is

This repo contains the **CareFlow agent source code** — the actual ADK `LlmAgent`, `SequentialAgent`, `ParallelAgent`, and `LoopAgent` implementations that power the system. All 8 sub-agents are fully implemented with real AlloyDB integration, Agentic RAG (HyDE + Hybrid + Self-RAG), openFDA drug interaction checking, and 7-layer safety.

## Architecture

```
root_agent (LlmAgent, gemini-2.5-flash)
│
├── Workflows (composite)
│   ├── post_visit_sequential   — [Task ∥ Schedule] → Medical Info → Diet → Caregiver
│   ├── pre_visit_parallel      — Health Insight ∥ Medical Info
│   ├── symptom_workflow        — Symptom Triage → Caregiver escalation
│   └── adherence_loop_agent    — LoopAgent (daily medication monitoring)
│
└── Standalone agents (single-intent routing)
    ├── health_insight_agent    — Trend analysis, proactive insights (AlloyDB timeseries)
    ├── diet_nutrition_agent    — Personalized diet + food-drug interaction
    ├── symptom_triage_agent    — 3-level urgency classification, safe defaults
    ├── task_agent              — Medication extraction + openFDA 3-layer DDI
    ├── schedule_agent          — Appointment booking & reminders
    ├── medical_info_agent      — Agentic RAG (HyDE + Hybrid + Self-RAG) over visit history
    └── caregiver_agent         — Caregiver notifications & status reports
```

## Key Technical Features

### Agentic RAG Pipeline (S-tier)
```
User Query
  → HyDE (Gemini Flash generates hypothetical clinical note)
  → Hybrid Search (pgvector Dense + PostgreSQL BM25 in parallel)
  → RRF Fusion (Reciprocal Rank Fusion, k=60)
  → Self-RAG Reflection (YES/PARTIAL/NO verdict per chunk)
  → Confidence Tiering (HIGH ≥0.78 / MEDIUM 0.6-0.78 / LOW <0.6 refuse)
  → Cross-patient post-retrieval assertion (defense-in-depth)
```
- Gemini `text-embedding-005` (768d) with **asymmetric task_type** (RETRIEVAL_DOCUMENT/QUERY)
- HNSW index (m=16, ef_construction=64) on AlloyDB pgvector
- 46-entry medical synonym map (symptoms, labs, DM2+HTN drug classes)
- Graceful degradation: HyDE miss → raw query; BM25 miss → dense-only; embed fail → keyword

### Drug Interaction (3-Layer Cascade)
```
Layer 1: openFDA Drug Labels API (real-time, FDA-authorized, free)
Layer 2: AlloyDB DDI corpus (if loaded)
Layer 3: Hardcoded _KNOWN_INTERACTIONS (offline last resort)
```
- Replaced deprecated RxNav API (404'd January 2024) with openFDA
- Severity inference: contraindications → CONTRAINDICATED, warnings → HIGH, interactions → MODERATE
- HITL trigger on any interaction detection

### AlloyDB Integration
- Real PostgreSQL with pgvector extension on Google Cloud AlloyDB
- 10-table schema with UUID primary keys, timeseries health metrics
- Rajesh Sharma seed data: 5 meds, 3 visits, 4 appointments, 360 health metrics (90-day)
- `_serialize_row` handles UUID/date/Decimal → JSON-safe types
- `_resolve_patient_id` maps LLM-generated placeholder IDs to real UUIDs

## Project structure

```
careflow/
├── agent.py                        # root_agent entry point (ADK convention)
├── agents/
│   ├── health_insight/             # Trend analysis, proactive insights
│   ├── diet_nutrition/             # Personalized diet + food-drug interaction
│   ├── symptom_triage/             # 3-level urgency classification
│   ├── adherence_loop/             # LoopAgent — medication monitoring
│   ├── task/                       # Medication extraction + DDI (openFDA 3-layer)
│   ├── schedule/                   # Appointment management
│   ├── medical_info/               # Agentic RAG over visit history
│   ├── caregiver/                  # Caregiver notifications
│   ├── safety/                     # SafetyPlugin, HITL, guardrails, scope judge
│   └── shared/                     # openfda_api, rxnorm_api, patient_utils
├── schemas/                        # Pydantic output schemas
├── db/                             # AlloyDB client (query_dict, execute_write)
└── tests/                          # Unit tests
```

## Intent routing

| Intent | Trigger examples | Delegates to |
|---|---|---|
| POST_VISIT | "doctor changed my medication..." | `post_visit_sequential` |
| INSIGHT_REQUEST | "how has my blood pressure been trending" | `health_insight_agent` |
| DIET_QUERY | "what can I eat for lunch" | `diet_nutrition_agent` |
| SYMPTOM_REPORT | "I'm feeling dizzy" | `symptom_workflow` |
| ADHERENCE_CHECK | "did I take my medication" | `adherence_loop_agent` |
| PRE_VISIT | "prepare summary for next visit" | `pre_visit_parallel` |
| STATUS_CHECK | "when is my next appointment" | `schedule_agent` |
| QUERY | "what did the doctor say last time" | `medical_info_agent` |
| CAREGIVER_QUERY | "how has my father been doing" | `medical_info_agent → caregiver_agent` |

## Safety layers

1. **Hybrid 2-Layer scope filter** — Fast regex prefilter + Gemini Flash LLM-as-Judge
2. **Prompt injection detection** — 10 regex patterns
3. **PII scan + masking** — Aadhaar, Indian phone, email (masked before reaching LLM)
4. **Cross-patient access block** — UUID resolution + session state + post-retrieval assertion
5. **HITL gate** — 4-level risk (LOW/MED/HIGH/CRITICAL), confirmation loop with yes/no
6. **Deterministic guardrails** — dosage range, allergy-food cross-check, symptom auto-escalation
7. **Medical disclaimer auto-injection** — dual-layer (safety plugin + per-agent)

## Quick start

```bash
# Install dependencies
pip install google-adk google-genai python-dotenv pytest

# Set credentials (Vertex AI via gcloud ADC)
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Run unit tests
python -m pytest careflow/tests/ -v

# Run end-to-end smoke test (3 core scenarios)
python test_e2e.py

# Run full 9-scenario test (needs higher rate limit)
python test_e2e.py --full

# Start ADK web UI
adk web .
```

## Model selection

Root agent defaults to `gemini-2.5-flash` for demo / testing (higher rate limits). Switch to `gemini-2.5-pro` for production:

```bash
CAREFLOW_ROOT_MODEL=gemini-2.5-pro adk web .
```

Sub-agents use Flash with per-agent temperature tuning:
- `symptom_triage`: 0.1 (deterministic safety classification)
- `health_insight`: 0.2 (consistent trend analysis)
- `diet_nutrition`: 0.4 (some variety in recommendations)
- `adherence_loop`: 0.1 (deterministic adherence checks)

## Team & integration

| Agent | Owner | Status |
|---|---|---|
| root_agent + orchestration | Somi | ✅ Complete |
| health_insight | Somi | ✅ Complete |
| diet_nutrition | Somi | ✅ Complete |
| symptom_triage | Somi | ✅ Complete |
| adherence_loop (LoopAgent) | Somi | ✅ Complete |
| safety + HITL + guardrails | Somi | ✅ Complete |
| Agentic RAG (HyDE+Hybrid+Self-RAG) | Somi | ✅ Complete |
| openFDA 3-layer DDI | Somi | ✅ Complete |
| schedule | Lavanya | ✅ Integrated |
| caregiver | Deeptesha | ✅ Integrated |
| task | thatengineerguy | ✅ Integrated + Fixed |
| medical_info (RAG) | thatengineerguy | ✅ Integrated + Rewritten |

---

*Built for Google Cloud Gen AI Academy APAC — Cohort 1 Hackathon*
