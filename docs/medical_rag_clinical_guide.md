# Medical RAG Clinical Safety & Compliance Guide
## CareFlow Medical Info Agent — Agentic RAG 임상 검증 문서

**Reviewer / 검토자:** Dr. Ateev Mehrotra, MD, MPH
Harvard Medical School / Beth Israel Deaconess Medical Center
Healthcare AI & Clinical Decision Support

**Document version:** 1.0
**Review date:** 2026-04-05
**Scope:** DM2 (Type 2 Diabetes Mellitus) + HTN (Hypertension) longitudinal care
**Status:** Clinical review — implementation guidance, non-binding until IRB sign-off

---

## 0. Executive Summary (요약)

CareFlow의 Agentic RAG는 일반 도메인 RAG와 근본적으로 다른 제약을 가집니다. 의료 텍스트는 (1) 부정문(negation)과 (2) 시간축(temporality), (3) 약어 밀도, (4) 환자 간 격리(cross-patient isolation), 그리고 (5) 임상적 유해 가능성(clinical harm potential)이 동시에 걸려 있습니다. 이 문서는 CareFlow가 DM2 + HTN 환자를 대상으로 한 longitudinal information retrieval을 수행할 때 반드시 지켜야 할 임상 안전 요구사항을 정리합니다.

General-domain RAG patterns (top-k cosine + LLM summarize) are **insufficient and potentially unsafe** in this setting. The system must enforce negation-aware retrieval, temporal grounding, and a mandatory "non-prescriptive" output contract.

---

## 1. Medical RAG 특수 요구사항 / Special Requirements

### 1.1 임상 문서 특성 (Clinical Document Characteristics)

| 문서 유형 | 구조적 특성 | RAG 취급 주의점 |
|---|---|---|
| **Discharge Summary** | HPI, PMH, Hospital Course, Medications on Discharge, Follow-up | "Medications on Discharge" 섹션은 **최신 처방의 source of truth**. 반드시 섹션 경계를 보존하며 chunking. |
| **Progress Note (SOAP)** | Subjective / Objective / Assessment / Plan | A/P 섹션만 임상 의사결정 근거. S 섹션은 환자 주관 표현 — factual claim으로 간주 금지. |
| **Visit Record / Outpatient Note** | Chief complaint, Vitals, Assessment, Orders | Vitals는 timestamp + unit 필수 동반. |
| **Lab Report** | Analyte, value, unit, reference range, flag(H/L) | 값만 임베딩하지 말고 reference range와 함께 chunk. |
| **Imaging Report** | Findings / Impression | Impression이 요약, Findings가 raw. RAG는 Impression 우선. |
| **Medication List** | Drug, dose, route, frequency, start/stop date | 반드시 **구조화 저장**, free-text embedding 보조. |

**핵심 원칙:** 임상 문서는 **section-aware chunking**이 필수입니다. 512-token sliding window는 SOAP 경계를 부숩니다. 권장: `section → sub-section → semantic chunk` 3단계 계층.

### 1.2 약물명 정규화 (Drug Name Normalization)

의료 RAG에서 **가장 흔한 실패 원인**입니다. 한 환자 차트 안에서 동일 약물이 brand / generic / abbreviation 3가지로 기록됩니다.

Required normalization pipeline:
1. **RxNorm RXCUI 매핑** (미국) 또는 **WHO ATC code** (국제)
2. 인도 시장 고려: Indian brand names (예: `Glyciphage` → `Metformin`, `Amlopres` → `Amlodipine`)
3. Ingredient-level 저장: `Glycomet-GP 2` → `{metformin: 500mg, glimepiride: 2mg}`
4. Salt form 구분: `Metoprolol tartrate` vs `Metoprolol succinate` — 임상적으로 **다른 약**
5. 복합제 분해: combination pills must be decomposed into components before retrieval

```
Embed key: "metformin 500mg PO BID"  (normalized)
Display:   "Glyciphage 500 (metformin)"  (original + normalized)
Metadata:  rxcui=6809, atc=A10BA02, salt=hydrochloride
```

### 1.3 임상 약어 확장 (Clinical Abbreviation Expansion)

Query-time과 index-time 양쪽에서 확장해야 합니다. **Index-time만 하면 환자 질문을 못 잡고, Query-time만 하면 노트의 약어를 못 잡습니다.**

| Abbrev | Expansion | 주의 (ambiguity) |
|---|---|---|
| BP | Blood Pressure | — |
| HR | Heart Rate | **경고:** "HR" = Hazard Ratio in research notes |
| RR | Respiratory Rate | RR = Relative Risk in lit |
| T | Temperature | T = Tumor stage in onc |
| Hb / Hgb | Hemoglobin | — |
| HbA1c / A1c | Glycated hemoglobin | — |
| FBS / FPG | Fasting Blood Sugar / Fasting Plasma Glucose | — |
| PPBS / PPG | Postprandial Blood Sugar | — |
| RBS | Random Blood Sugar | — |
| BG / BGL | Blood Glucose (Level) | — |
| eGFR | estimated Glomerular Filtration Rate | — |
| ACR / UACR | Urine Albumin-to-Creatinine Ratio | — |
| LDL / HDL | Low/High-Density Lipoprotein | — |
| TG | Triglycerides | — |
| BMI | Body Mass Index | — |
| DM / DM2 / T2DM | Diabetes Mellitus / Type 2 | DM = Diabetes vs Dermatomyositis |
| HTN | Hypertension | — |
| CAD | Coronary Artery Disease | — |
| CKD | Chronic Kidney Disease | — |
| CHF / HFrEF / HFpEF | Heart Failure (reduced / preserved EF) | — |
| MI | Myocardial Infarction | **경고:** MI = Mitral Insufficiency |
| TIA / CVA | Transient Ischemic Attack / Stroke | — |
| OSA | Obstructive Sleep Apnea | — |
| Rx | Prescription / Therapy | — |
| Dx / Hx / Tx / Sx | Diagnosis / History / Treatment / Symptoms | — |
| c/o | complains of | — |
| s/p | status post | — |
| w/ w/o | with / without | **negation marker** |
| h/o | history of | **negation target** |
| PMH / PSH | Past Medical / Surgical History | — |
| BID / TID / QID / QD / QHS / PRN | 2x/3x/4x/1x per day, at bedtime, as needed | **dose frequency — mandatory normalize** |
| PO / IV / IM / SC / SL | Oral / IV / IM / Subcut / Sublingual | route |

**Rule:** ambiguity가 있는 약어는 섹션 컨텍스트로 disambiguate. 예를 들어 `HR` in Vitals section → Heart Rate, `HR` in a research summary → Hazard Ratio.

### 1.4 Temporal Reasoning (시간 추론)

이것이 일반 RAG와 임상 RAG를 가르는 핵심입니다. "환자는 metformin을 복용한다"는 **지금**인가 **2년 전**인가? 임상 질문의 80%는 temporal grounding을 요구합니다.

Requirements:
- Every retrieved chunk **must carry** `encounter_date`, `document_date`, and when possible `clinical_event_date` (e.g. medication start date ≠ note date).
- Temporal operators in query: `latest`, `prior to`, `since`, `within last N months`.
- **"Current medication" 질문 시:** most recent discharge summary OR most recent med reconciliation 기준, 단 after `stop_date` filter.
- **Diagnosis onset:** first mention date ≠ diagnosis date. Use explicit `dx_date` field when ICD-coded, fall back to earliest mention with "newly diagnosed / newly found" phrase matching.
- **Lab trends:** retrieve as time series, not as isolated chunks. HbA1c trajectory is clinically meaningful; a single value is not.

Implementation pattern:
```
retrieve(query, patient_id,
         time_filter={"as_of": today, "lookback_months": 12},
         prefer_recent=True,
         recency_decay=0.9 / month)
```

### 1.5 Negation Handling (부정 처리)

**가장 위험한 실패 모드.** Dense embeddings는 "no history of MI"와 "history of MI"를 **거의 동일하게** 매핑합니다. RAG가 이것을 구분하지 못하면 환자에게 존재하지 않는 병력을 귀속시킵니다 — **명백한 임상 위해**.

Required controls:
1. **NegEx / ConText algorithm** or modern equivalent (e.g., medspaCy `negex`) at ingest time.
2. Chunk metadata field: `negated: bool`, `hypothetical: bool`, `historical: bool`, `subject: {patient | family | other}`.
3. Retrieval must **re-rank** such that negated mentions are surfaced separately from asserted mentions when the query is about positive assertion.
4. LLM prompt must receive negation flags explicitly:
   ```
   [CHUNK | asserted=False, negated=True]
   "Patient denies chest pain, no history of MI."
   ```
5. Family history trigger words: `father`, `mother`, `sibling`, `FHx` → `subject=family`, never confuse with patient's own Hx.

### 1.6 Dose / Unit / Frequency 파싱

Must be parsed into a structured tuple at ingest:

```
{
  drug: "metformin",
  dose_amount: 500,
  dose_unit: "mg",
  route: "PO",
  frequency: "BID",
  frequency_per_day: 2,
  prn: false,
  start_date: "2024-06-12",
  stop_date: null,
  indication: "T2DM"
}
```

- **Unit conversion** must be explicit. `0.5 g` and `500 mg` are the same; the LLM cannot be trusted to arithmetic convert at query time.
- **Mg vs mcg** errors are a known medication error class — treat as high-severity validation.
- **Insulin units** ("U" / "IU") must NEVER be abbreviated as "u" — known sentinel event cause.
- **BP readings:** parse as `systolic/diastolic mmHg` with timestamp and position (sitting/standing — orthostatic matters in elderly HTN).
- **Glucose:** always carry unit (`mg/dL` vs `mmol/L`) — 18:1 conversion factor, errors are catastrophic.

---

## 2. Medical Synonym / Query Reformulation Map

CareFlow의 대상 질환(DM2 + HTN)과 인접 심혈관/신장/대사 영역을 커버하는 **최소 40개** 매핑입니다. Query reformulation layer는 lay term → clinical term → abbreviation 3방향 expansion을 수행해야 합니다.

### 2.1 Symptoms / 증상

| Lay / Patient term | Clinical synonyms |
|---|---|
| 1. chest pain | angina, angina pectoris, chest tightness, cardiac discomfort, retrosternal pain, chest pressure |
| 2. shortness of breath | dyspnea, SOB, breathlessness, DOE (dyspnea on exertion), orthopnea, PND |
| 3. dizziness / lightheaded | vertigo, presyncope, syncope, orthostatic hypotension symptoms |
| 4. leg swelling | pedal edema, bilateral lower extremity edema, peripheral edema, fluid retention |
| 5. tiredness | fatigue, lethargy, asthenia, malaise, decreased energy |
| 6. headache | cephalalgia, HA, HTN headache, occipital headache |
| 7. blurry vision | blurred vision, visual disturbance, diabetic retinopathy symptoms |
| 8. numbness / tingling in feet | peripheral neuropathy, paresthesia, diabetic neuropathy, stocking-glove distribution |
| 9. frequent urination | polyuria, urinary frequency, nocturia |
| 10. excessive thirst | polydipsia |
| 11. unintended weight loss | unexplained weight loss, cachexia |
| 12. palpitations | tachycardia, irregular heartbeat, arrhythmia sensation |
| 13. leg pain on walking | intermittent claudication, PAD symptoms |
| 14. slow-healing wound | diabetic foot ulcer, delayed wound healing, nonhealing ulcer |

### 2.2 Labs / Measurements

| Lay term | Clinical synonyms |
|---|---|
| 15. blood sugar | glucose, BG, BGL, plasma glucose, FBS, FPG, PPBS, PPG, RBS, HbA1c, A1c, glycated hemoglobin, estimated average glucose (eAG) |
| 16. high BP / high pressure | hypertension, HTN, elevated blood pressure, systolic hypertension, stage 1/2 HTN |
| 17. low BP | hypotension, orthostatic hypotension |
| 18. cholesterol | lipid panel, LDL, HDL, triglycerides, TG, non-HDL, lipid profile |
| 19. kidney function | renal function, creatinine, serum Cr, eGFR, BUN, UACR, urine microalbumin, CKD stage |
| 20. liver function | LFT, hepatic panel, AST, ALT, ALP, bilirubin |
| 21. weight / obesity | BMI, body mass index, adiposity, overweight, class I/II/III obesity |
| 22. heart rate | HR, pulse, pulse rate, bpm |

### 2.3 Conditions / 진단

| Lay term | Clinical synonyms |
|---|---|
| 23. diabetes | DM, DM2, T2DM, type 2 diabetes mellitus, NIDDM, hyperglycemia, prediabetes, impaired fasting glucose, IFG, IGT |
| 24. high blood pressure | hypertension, HTN, essential hypertension, primary hypertension |
| 25. heart disease | CAD, coronary artery disease, ischemic heart disease, IHD, ASCVD, atherosclerotic cardiovascular disease |
| 26. heart attack | myocardial infarction, MI, NSTEMI, STEMI, acute coronary syndrome, ACS |
| 27. stroke | CVA, cerebrovascular accident, ischemic stroke, TIA, transient ischemic attack |
| 28. heart failure | CHF, congestive heart failure, HFrEF, HFpEF, cardiomyopathy |
| 29. kidney disease | CKD, chronic kidney disease, diabetic nephropathy, diabetic kidney disease, DKD |
| 30. nerve damage (diabetic) | diabetic neuropathy, DPN, peripheral neuropathy, autonomic neuropathy |
| 31. eye damage (diabetic) | diabetic retinopathy, NPDR, PDR, diabetic macular edema |

### 2.4 Medications / 약물

| Lay term | Clinical synonyms (DM2 + HTN focus) |
|---|---|
| 32. diabetes meds / sugar medicine | antidiabetic agents, oral hypoglycemic agents, OHA, metformin (Glycomet, Glyciphage), sulfonylureas (glimepiride, gliclazide, glibenclamide), DPP-4 inhibitors (sitagliptin, vildagliptin, linagliptin), SGLT2 inhibitors (dapagliflozin, empagliflozin, canagliflozin), GLP-1 RA (liraglutide, semaglutide, dulaglutide), TZDs (pioglitazone), insulin (glargine, aspart, lispro, NPH, regular), meglitinides |
| 33. BP meds / pressure medicine | antihypertensives, ACE inhibitors (enalapril, ramipril, lisinopril), ARBs (telmisartan, losartan, olmesartan), CCBs (amlodipine, nifedipine, cilnidipine), beta-blockers (metoprolol, bisoprolol, carvedilol, atenolol), thiazide diuretics (HCTZ, chlorthalidone, indapamide), loop diuretics (furosemide, torsemide), alpha-blockers, central agents |
| 34. heart medication | cardiovascular drugs, cardioprotective agents, antianginals (nitrates, isosorbide mononitrate), antiplatelets (aspirin, clopidogrel), statins (atorvastatin, rosuvastatin, simvastatin), beta-blockers |
| 35. blood thinner | anticoagulant, antiplatelet, warfarin, DOAC, apixaban, rivaroxaban, dabigatran, aspirin, clopidogrel |
| 36. cholesterol medicine | statin, HMG-CoA reductase inhibitor, atorvastatin, rosuvastatin, ezetimibe, fibrate, fenofibrate |
| 37. water pill | diuretic, thiazide, loop diuretic, furosemide, HCTZ, spironolactone |

### 2.5 Behaviors / Adherence

| Lay term | Clinical synonyms |
|---|---|
| 38. missed dose / skipped pill | non-adherence, medication non-compliance, MPR (medication possession ratio) drop, treatment gap |
| 39. stopped medication | discontinuation, treatment cessation, D/C, self-discontinuation |
| 40. diet | medical nutrition therapy, MNT, carbohydrate counting, DASH diet, dietary adherence |
| 41. exercise | physical activity, aerobic exercise, MET-minutes, lifestyle modification |
| 42. smoking | tobacco use, smoking status, pack-years, current/former/never smoker |
| 43. drinking | alcohol use, AUDIT score, standard drinks/week |
| 44. low sugar / hypo | hypoglycemia, hypoglycemic event, level 1/2/3 hypoglycemia, Whipple's triad |
| 45. high sugar / hyper | hyperglycemia, DKA (if severe), HHS |

**Implementation note:** this table should be stored as a structured synonym set (JSON/YAML), fed into (a) query expansion at retrieval time and (b) a BM25 sparse index alongside dense embeddings. **Pure dense retrieval will miss lay-to-clinical mappings** — hybrid retrieval is mandatory.

---

## 3. 의료 데이터 프라이버시 가이드 / Privacy Guide

### 3.1 PII / PHI 필터링 원칙

HIPAA Safe Harbor defines 18 PHI identifiers; India's **DPDP Act 2023** defines "personal data" and "sensitive personal data" with explicit consent requirements for health data. CareFlow must comply with both if operating in India with cross-border processing.

Minimum filtering rules:
1. **Never embed raw identifiers.** Strip name, MRN, phone, email, address, date-of-birth (retain year only, bucket ages ≥ 90 to "90+"), face photos, biometric IDs, vehicle/device serials, URLs, IPs.
2. **Encounter IDs** may be retained as opaque internal keys but must not be derivable from patient identity.
3. **Free-text de-identification:** run a clinical NER (e.g., Presidio + medspaCy) over every chunk *before* embedding. Flag residual PHI risk with a probability score.
4. **Dates:** shift dates by a per-patient random offset (±365 days) if using data for fine-tuning or analytics; keep true dates only in the operational store under access control.
5. **Re-identification risk:** rare diagnoses + small geography is re-identifying even without name. Apply k-anonymity ≥ 5 on any aggregate export.

### 3.2 임베딩 저장 시 보안

- **Encryption at rest:** AES-256 for the vector store; KMS-managed keys with rotation.
- **Encryption in transit:** TLS 1.3 only.
- **Embeddings are not anonymous.** Research (Morris et al., Song & Raghunathan) shows text can be reconstructed from embeddings. Treat embedding vectors as **PHI-equivalent**.
- Store vectors in a **separate logical namespace per tenant** (hospital/clinic), never commingled.
- Access logging: every retrieval call logged with `user_id`, `patient_id`, `query_hash`, `retrieved_chunk_ids`, `timestamp`. Retention per HIPAA: 6 years minimum; DPDP: as long as purpose is active + consented.

### 3.3 Cross-patient Data Isolation

This is non-negotiable. A single retrieval for Patient A **must never** surface a chunk from Patient B, even by accident.

Enforcement layers (defense in depth):
1. **Mandatory filter at query construction:** `WHERE patient_id = :pid` injected by the retrieval wrapper, not by the caller.
2. **Index partitioning:** one vector index per patient, or hard filter in the ANN engine (e.g., pgvector with row-level security, Pinecone namespaces).
3. **Post-retrieval assertion:** after retrieval, assert `all(chunk.patient_id == expected_pid)` — fail closed if violated.
4. **Unit test:** red-team test that issues a query known to match Patient B's content while scoped to Patient A — must return zero Patient B chunks.
5. **No global fine-tuning on patient text** without de-identification and explicit consent; memorization leakage is a documented risk.

### 3.4 DPDP Act 2023 (India) / HIPAA Alignment

| Principle | HIPAA (US) | DPDP 2023 (India) | CareFlow action |
|---|---|---|---|
| Lawful basis | Treatment, Payment, Operations (TPO) | Consent or "legitimate use" | Explicit patient consent at onboarding + purpose-specific re-consent for AI use |
| Minimum necessary | § 164.502(b) | Principle of minimization | Retrieve only chunks needed to answer the query; no wholesale chart dumps to LLM |
| Access & correction | Patient right of access | Data Principal right to access, correction, erasure | Expose patient self-service API |
| Breach notification | 60 days | 72 hours to DPB | Automated incident pipeline |
| Cross-border transfer | BAA w/ cloud | Restricted to notified countries | Use in-region (India) inference endpoints for India patients |
| Data Protection Officer | Privacy Officer | Mandatory DPO for Significant Data Fiduciaries | Assign DPO for CareFlow deployment |
| Children | Under HIPAA parental rules | Verifiable parental consent under 18 | Age flag in patient record |

---

## 4. 임상적 안전 필터 / Clinical Safety Filters

### 4.1 RAG 출력에서의 금지 패턴 (Prohibited Output Patterns)

The agent is **informational, not prescriptive**. The following outputs are forbidden and must be blocked at a post-generation filter:

| Forbidden pattern | Example (block) | Allowed reformulation |
|---|---|---|
| Direct dosing instruction | "Take 1000 mg metformin twice daily." | "Your chart shows metformin 1000 mg BID as your current prescription. Confirm with your physician before any change." |
| New therapy recommendation | "You should start an SGLT2 inhibitor." | "SGLT2 inhibitors are one class discussed in guidelines for patients like you; this is a decision for your physician." |
| Dose titration advice | "Increase your insulin by 2 units." | Block. Refer to prescriber. |
| Diagnostic conclusion | "You have diabetic nephropathy." | "Your recent UACR was elevated. Your physician may want to evaluate for kidney involvement." |
| Stopping a drug | "You can stop your BP medication if BP is normal." | Block. High harm potential. |
| Emergency triage | "It is not serious." (for chest pain, stroke sx, hypoglycemia) | Block. Escalate: "Please contact emergency services / your physician immediately." |

### 4.2 Mandatory Insertions

Every response must include, programmatically enforced at the end of generation:
1. A **non-prescriptive disclaimer**: *"This information is drawn from your medical record and is for educational support only. It is not a substitute for clinical judgment. Please consult your physician before making any change to your medications or care plan."*
2. If the response discusses **red-flag symptoms** (chest pain, severe SOB, focal neuro deficit, severe hypoglycemia, BP > 180/120, glucose > 300 mg/dL), prepend an **urgent care trigger**: *"The symptoms you describe may require urgent evaluation. If they are occurring now, call your emergency line."*
3. Citations: every clinical claim must link to a specific chunk ID and document date. Uncited claims must be stripped.

### 4.3 Confidence Score Interpretation

Do not expose raw cosine similarity to clinicians — it is not calibrated. Instead:

| Tier | Criteria | UI treatment |
|---|---|---|
| **High** | ≥ 2 independent chunks from distinct documents, same assertion, recent (< 12 mo), no negation conflict | Show answer with citations |
| **Medium** | 1 chunk or older data or minor conflict | Show with explicit "limited evidence in record" badge |
| **Low** | No retrieved support, or conflicting negation, or pre-guideline-era data | **Do not answer clinically.** Respond: "I could not find reliable information in your record about this. Please ask your physician." |
| **Conflict** | Contradictory chunks (e.g., one says "on metformin", another says "stopped metformin") | Surface **both** with dates; do not auto-resolve |

Conflict resolution must be **explicit and dated**, never silent.

### 4.4 Hallucination Guardrails

- **Closed-book disabled.** The LLM must answer only from retrieved context. System prompt enforces `if context is empty: refuse`.
- **Numeric values must be verbatim** from chunk or explicitly computed with a shown formula. No paraphrased numbers.
- **Drug names must match normalized ingredient list.** Post-generation NER re-check: every drug mentioned in output must appear in retrieved chunks.
- **Date claims must cite source date.**

---

## 5. Minimum Requirements Checklist (체크리스트 20개)

A medical RAG system shipping into a DM2 + HTN care workflow must satisfy all 20:

- [ ] **1. Section-aware chunking** preserving SOAP / discharge / med-list boundaries.
- [ ] **2. Drug name normalization** to RxNorm / ATC with brand ↔ generic ↔ ingredient mapping, including Indian brands.
- [ ] **3. Structured medication extraction** (drug, dose, unit, route, frequency, start/stop) — not free-text only.
- [ ] **4. Clinical abbreviation dictionary** applied at both index-time and query-time.
- [ ] **5. Negation detection** (NegEx/ConText) with `negated`, `hypothetical`, `historical`, `subject` metadata on every chunk.
- [ ] **6. Temporal metadata** (`document_date`, `encounter_date`, `event_date`) on every chunk; retrieval supports time filters.
- [ ] **7. Hybrid retrieval** (dense + BM25 sparse) with synonym expansion — not dense-only.
- [ ] **8. Per-patient index isolation** with hard patient_id filter and post-retrieval assertion.
- [ ] **9. PHI stripping** before embedding; embeddings treated as PHI-equivalent.
- [ ] **10. Encryption** at rest (AES-256) and in transit (TLS 1.3); KMS key rotation.
- [ ] **11. Audit logging** of every retrieval (user, patient, query, chunk IDs, timestamp), 6-year retention.
- [ ] **12. Consent capture** aligned with DPDP 2023 + HIPAA; purpose-specific AI consent.
- [ ] **13. Closed-book disabled** — LLM refuses if no retrieved context.
- [ ] **14. Non-prescriptive output contract** — no dosing, titration, start/stop, or diagnostic conclusions.
- [ ] **15. Mandatory disclaimer + red-flag escalation** inserted programmatically in every response.
- [ ] **16. Citation enforcement** — every clinical claim linked to chunk ID + document date; uncited claims stripped.
- [ ] **17. Confidence tiering** (High / Medium / Low / Conflict) surfaced to UI; Low = refuse clinically.
- [ ] **18. Conflict surfacing** — contradictory chunks shown with dates, no silent resolution.
- [ ] **19. Unit & dose validation** — mg vs mcg, mg/dL vs mmol/L, insulin "U" never "u"; arithmetic not delegated to LLM.
- [ ] **20. Red-team evaluation suite** covering: cross-patient leakage, negation flips, temporal confusion (old med listed as current), dose errors, brand/generic mismatch, lay-term miss, and prompt injection inside clinical notes. Pass threshold defined and signed off by clinical lead before go-live.

---

## 6. Closing Notes (검토자 코멘트)

CareFlow의 목표 — DM2 + HTN 환자에게 longitudinal care continuity를 제공하는 것 — 은 임상적으로 가치가 크고, Agentic RAG가 기여할 수 있는 명확한 use case입니다. 다만 이 문서에서 정리한 제약은 **optional best practice가 아니라 minimum viable safety floor**입니다. 특히 (1) negation handling, (2) cross-patient isolation, (3) non-prescriptive output contract 세 가지는 go-live 전에 독립적으로 검증되지 않은 상태로 배포되어서는 안 됩니다.

The clinical value of CareFlow is real, and so is the harm surface. Build the safety scaffolding before you optimize retrieval quality — once a cross-patient leak or a negation flip reaches a patient, no model quality gain will recover the trust.

I recommend a staged rollout: (1) clinician-in-the-loop pilot (n ≤ 20 patients, every response reviewed by a physician before release), (2) supervised release (physician sees every response but approval is implicit unless flagged), (3) patient-facing release only after a documented adverse event rate below a prespecified threshold over ≥ 3 months.

— **Ateev Mehrotra, MD, MPH**
Harvard Medical School / Beth Israel Deaconess Medical Center
Clinical review, 2026-04-05
