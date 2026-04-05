# CareFlow Agents

Multi-agent healthcare post-visit care coordination system built on Google ADK.

> Part of **CareFlow** — Google Cloud Gen AI Academy APAC Edition, Cohort 1 Hackathon.

---

## What this repo is

This repo contains the **CareFlow agent source code** — the actual ADK `LlmAgent`, `SequentialAgent`, `ParallelAgent`, and `LoopAgent` implementations that power the system. Design docs, diagrams, and references live in the main architecture repo; datasets and download scripts live in the `Data` repo.

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
    ├── health_insight_agent
    ├── diet_nutrition_agent
    ├── symptom_triage_agent
    ├── task_agent              (placeholder — to be wired on integration)
    ├── schedule_agent          (placeholder — to be wired on integration)
    ├── medical_info_agent      (placeholder — to be wired on integration)
    └── caregiver_agent         (placeholder — to be wired on integration)
```

## Project structure

```
careflow/
├── agent.py                        # root_agent entry point (ADK convention)
├── agents/
│   ├── health_insight/             # Trend analysis, proactive insights
│   ├── diet_nutrition/             # Personalized diet + food-drug interaction
│   ├── symptom_triage/             # 3-level urgency classification
│   ├── adherence_loop/             # LoopAgent — medication monitoring
│   └── safety/                     # SafetyPlugin, HITL, guardrails, scope judge
├── schemas/                        # Pydantic output schemas
├── data/                           # ICD-11 mapping, RxNorm reference
└── tests/                          # 22 unit tests
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

1. **Hybrid 2-Layer scope filter** — Fast regex prefilter + Gemini Flash LLM-as-Judge (Dr. Emily Watson's pattern)
2. **Prompt injection detection** — 10 regex patterns
3. **PII scan + masking** — Aadhaar, Indian phone, email (masked before reaching LLM)
4. **Cross-patient access block** — session state validation
5. **HITL gate** — 4-level risk (LOW/MED/HIGH/CRITICAL), confirmation loop with yes/no processing
6. **Deterministic guardrails** — dosage range validation, allergy-food cross-check, symptom auto-escalation
7. **Medical disclaimer auto-injection** — applied to any response touching diagnosis/prescription

## Quick start

```bash
# Install dependencies
pip install google-adk google-genai python-dotenv pytest

# Set credentials (Vertex AI via gcloud ADC)
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Run unit tests
python -m pytest careflow/tests/ -v

# Run end-to-end smoke test
python test_e2e.py

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

| Agent | Owner | Branch |
|---|---|---|
| root_agent | Somi | `main` |
| health_insight | Somi | `main` |
| diet_nutrition | Somi | `main` |
| symptom_triage | Somi | `main` |
| adherence_loop | Somi | `main` (LoopAgent Pattern 6) |
| safety + HITL + guardrails | Somi | `main` |
| schedule | Lavanya | `feature/schedule-agent` |
| caregiver | Deeptesha | `feature/caregiver-agent` |
| task | thatengineerguy | `feature/task-medical-info` |
| medical_info (RAG) | thatengineerguy | `feature/task-medical-info` |

Each teammate agent lands on its own feature branch. Placeholder stubs on `main` return realistic JSON so the full workflow runs end-to-end during development, and they get swapped out when feature branches are merged in.

## Rate limit notes

Vertex AI free tier is ~5 RPM for Pro and ~15 RPM for Flash. Enable billing and use Flash for the root agent to avoid 429 during demo.

---

*Built for Google Cloud Gen AI Academy APAC — Cohort 1 Hackathon*
