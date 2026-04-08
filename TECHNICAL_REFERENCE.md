# CareFlow — AI Care Coordinator for Chronic Disease Patients

> One doctor visit. Eight AI agents. Continuous care.

<p align="center">
  <a href="https://careflow-892626469440.us-central1.run.app">
    <img src="https://img.shields.io/badge/Live%20Demo-Cloud%20Run-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="Live Demo" />
  </a>
</p>

**Live Demo:** https://careflow-892626469440.us-central1.run.app

<!-- Replace with actual screenshot -->
<!-- ![CareFlow Screenshot](docs/screenshot.png) -->

---

## The Problem

- **537 million** adults worldwide live with diabetes — projected to reach 783M by 2045
- **50%** of chronic disease patients stop following treatment plans within 6 months
- The gap between "what the doctor said" and "what the patient actually does" costs **$528B annually** in preventable complications

## The Solution

CareFlow bridges the post-visit care gap with **8 specialized AI agents** working as a coordinated care team. A single `root_agent` orchestrates the entire system — routing patient queries across 9 intent categories, automating medication tracking, diet planning, symptom triage, and caregiver alerts. Built on **real infrastructure**: AlloyDB with pgvector for clinical data, 3 MCP tool integrations, and Agentic RAG with HyDE + Hybrid Search + Self-RAG for medical information retrieval.

## Key Features

- **9-intent smart routing** — root_agent classifies and delegates to the right agent in one hop
- **Agentic RAG pipeline** — HyDE hypothetical document generation + Hybrid Search (dense + BM25) + RRF fusion + Self-RAG reflection with confidence tiering
- **7-layer safety system** — scope filtering, prompt injection detection, PII masking, cross-patient access block, HITL confirmation, deterministic guardrails, medical disclaimers
- **AlloyDB + pgvector** — 10-table schema with real patient data, HNSW vector index, 360-point timeseries health metrics
- **3 MCP integrations** — Google Calendar (appointments), Gmail (caregiver alerts), MCP Toolbox for Databases
- **Interactive health charts** — trend visualization for blood pressure, glucose, weight over time
- **Proactive health alerts** — anomaly detection triggers caregiver notifications automatically
- **STT voice input + TTS read-aloud** — accessible for elderly patients
- **openFDA drug interaction** — real-time 3-layer cascade (openFDA API + AlloyDB corpus + hardcoded fallback)

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

### Agentic RAG Pipeline

```
User Query
  → HyDE (Gemini Flash generates hypothetical clinical note)
  → Hybrid Search (pgvector Dense + PostgreSQL BM25 in parallel)
  → RRF Fusion (Reciprocal Rank Fusion, k=60)
  → Self-RAG Reflection (YES/PARTIAL/NO verdict per chunk)
  → Confidence Tiering (HIGH ≥0.78 / MEDIUM 0.6-0.78 / LOW <0.6 refuse)
  → Cross-patient post-retrieval assertion (defense-in-depth)
```

### Safety Layers

| Layer | Protection |
|-------|-----------|
| 1 | Hybrid 2-layer scope filter — fast regex prefilter + Gemini Flash LLM-as-Judge |
| 2 | Prompt injection detection — 10 regex patterns |
| 3 | PII scan + masking — Aadhaar, Indian phone, email masked before LLM |
| 4 | Cross-patient access block — UUID resolution + session state + post-retrieval assertion |
| 5 | HITL gate — 4-level risk (LOW/MED/HIGH/CRITICAL), confirmation loop |
| 6 | Deterministic guardrails — dosage range, allergy-food cross-check, symptom auto-escalation |
| 7 | Medical disclaimer auto-injection — dual-layer (safety plugin + per-agent) |

## Tech Stack

| Category | Technology |
|----------|-----------|
| Agent Framework | Google ADK (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent) |
| LLM | Gemini 2.5 Flash (sub-agents) / Gemini 2.5 Pro (root_agent production) |
| Embeddings | Gemini `text-embedding-005` (768d, asymmetric task_type) |
| Database | AlloyDB + pgvector (HNSW index, m=16, ef=64) |
| Vector Search | Hybrid: pgvector dense + PostgreSQL BM25 + RRF fusion |
| MCP Tools | MCP Toolbox for Databases, Google Calendar MCP, Gmail MCP |
| Drug Safety | openFDA Drug Labels API (real-time, FDA-authorized) |
| Deployment | Google Cloud Run + Docker |
| Frontend | ADK Web UI + Interactive Charts + STT/TTS |
| Testing | pytest (unit + e2e smoke tests) |

## Quick Start

```bash
# Install dependencies
pip install google-adk google-genai python-dotenv pytest

# Authenticate
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Run tests
python -m pytest careflow/tests/ -v

# Launch
adk web .
```

## Intent Routing

| Intent | Example | Agent |
|--------|---------|-------|
| POST_VISIT | "Doctor changed my medication..." | `post_visit_sequential` |
| INSIGHT_REQUEST | "How has my blood pressure been trending?" | `health_insight_agent` |
| DIET_QUERY | "What can I eat for lunch?" | `diet_nutrition_agent` |
| SYMPTOM_REPORT | "I'm feeling dizzy" | `symptom_workflow` |
| ADHERENCE_CHECK | "Did I take my medication?" | `adherence_loop_agent` |
| PRE_VISIT | "Prepare summary for next visit" | `pre_visit_parallel` |
| STATUS_CHECK | "When is my next appointment?" | `schedule_agent` |
| QUERY | "What did the doctor say last time?" | `medical_info_agent` |
| CAREGIVER_QUERY | "How has my father been doing?" | `caregiver_agent` |

## Team

**Team Inference Engines** — Google Cloud Gen AI Academy APAC Edition, Cohort 1

| Member | Contribution |
|--------|-------------|
| Somi | root_agent orchestration, Health Insight, Diet/Nutrition, Symptom Triage, Adherence Loop, Safety/HITL, Agentic RAG, openFDA DDI, integration |
| Deeptesha | Caregiver Agent + Gmail MCP |
| thatengineerguy | Task Agent + Medical Info Agent |
| Lavanya | Schedule Agent + Google Calendar MCP |

---

*Built for Google Cloud Gen AI Academy APAC — Cohort 1 Hackathon*
