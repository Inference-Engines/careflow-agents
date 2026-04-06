"""CareFlow Root Agent — 전체 오케스트레이터.

ADK 진입점. `adk web` 또는 `adk run`으로 실행 시 이 파일의 `root_agent` 변수를
자동으로 로드한다. 8개 서브에이전트 + 안전 레이어 + MCP 통합 완료.

All 8 sub-agents (fully implemented):
    - health_insight_agent   : trend analysis, proactive insights (AlloyDB)
    - diet_nutrition_agent   : personalized diet + food-drug interaction
    - symptom_triage_agent   : 3-level urgency classification, safe defaults
    - adherence_loop_agent   : LoopAgent — daily medication monitoring
    - task_agent             : medication extraction + openFDA 3-layer DDI
    - schedule_agent         : appointment booking + Google Calendar MCP
    - medical_info_agent     : Agentic RAG (HyDE+Hybrid+RRF+Self-RAG)
    - caregiver_agent        : caregiver notifications + Gmail MCP

ADK single-parent constraint: 모든 워크플로우용 인스턴스는 팩토리로 매번 새로
생성한다. 동일 인스턴스를 여러 parent 아래에 두면 런타임 에러가 난다.

설계 문서 / Design doc: CareFlow_System_Design_EN_somi.md
"""

from __future__ import annotations

# Rate limiter — 429 방어 (임포트만으로 자동 적용)
# Import alone auto-patches genai Client with retry + backoff
import careflow.rate_limiter  # noqa: F401

import os

# ─── Rate limiter: MUST be imported before any genai Client is created ───
# 429 RESOURCE_EXHAUSTED 방어: genai Client 생성 전에 반드시 임포트해야 함
import careflow.rate_limiter  # noqa: F401 — auto-patches google.genai on import

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from google.genai import types

# ─────────────────────────────────────────────────────────────────────────────
# Somi 담당 에이전트 — 팩토리 import
# Somi's agents — factory imports (fresh instances per workflow)
# ─────────────────────────────────────────────────────────────────────────────
from careflow.agents.health_insight.agent import build_health_insight_agent
from careflow.agents.diet_nutrition.agent import build_diet_nutrition_agent
from careflow.agents.symptom_triage.agent import build_symptom_triage_agent
from careflow.agents.adherence_loop.agent import adherence_loop_agent

# Lavanya 담당 에이전트 — feature/schedule-agent 브랜치에서 통합
# Lavanya's agent — integrated on feature/schedule-agent branch
from careflow.agents.schedule.agent import build_schedule_agent

# thatengineerguy 담당 에이전트 — feature/task-medical-info 브랜치에서 통합
# thatengineerguy's agents — integrated on feature/task-medical-info branch
from careflow.agents.task.agent import build_task_agent
from careflow.agents.medical_info.agent import build_medical_info_agent

# Deeptesha 담당 에이전트 — feature/caregiver-agent 브랜치에서 통합
# Deeptesha's agent — integrated on feature/caregiver-agent branch
from careflow.agents.caregiver.agent import build_caregiver_agent

# 안전 레이어 콜백 — 모든 에이전트에 일관 적용
# Safety layer callbacks — applied uniformly across agents
from careflow.agents.safety.plugin import before_model_callback, after_model_callback


# ─────────────────────────────────────────────────────────────────────────────
# ADK 인스턴스 생성 규칙 — Single-parent Constraint
# ADK Instance Rules — Single-parent Constraint
# ─────────────────────────────────────────────────────────────────────────────
# ADK 는 인스턴스마다 단일 parent 만 허용하므로, 여러 워크플로우에 동일 역할의
# 에이전트를 넣을 때는 매 호출마다 새 LlmAgent 인스턴스를 만들어야 한다.
# Since ADK enforces one parent per agent instance, we return a fresh LlmAgent
# on every call (using factories like build_task_agent) so each workflow gets its own object.


# ─────────────────────────────────────────────────────────────────────────────
# 워크플로우 정의 — Sequential / Parallel / Loop 조합
# Workflow definitions — Sequential / Parallel / Loop composition
# ─────────────────────────────────────────────────────────────────────────────

# POST_VISIT: [Task ∥ Schedule] → Medical Info → Diet → Caregiver
# 병렬로 추출하고 순차적으로 후처리하는 전형적인 post-visit 파이프라인.
post_visit_parallel = ParallelAgent(
    name="post_visit_parallel",
    sub_agents=[build_task_agent(suffix="_pv"), build_schedule_agent(suffix="_pv")],
    description="Task extraction and schedule booking run in parallel",
)

post_visit_sequential = SequentialAgent(
    name="post_visit_sequential",
    sub_agents=[
        post_visit_parallel,
        build_medical_info_agent(suffix="_pv"),
        build_diet_nutrition_agent(suffix="_pv"),
        build_caregiver_agent(suffix="_pv"),
    ],
    description="Full post-visit workflow: parallel extract → medical info → diet → caregiver",
)

# PRE_VISIT: Health Insight ∥ Medical Info → 의사용 사전 요약
pre_visit_parallel = ParallelAgent(
    name="pre_visit_parallel",
    sub_agents=[
        build_health_insight_agent(suffix="_prev"),
        build_medical_info_agent(suffix="_prev"),
    ],
    description="Health insight analysis and medical records retrieval in parallel",
)

# SYMPTOM: Triage → (필요 시) Caregiver 에스컬레이션
symptom_workflow = SequentialAgent(
    name="symptom_workflow",
    sub_agents=[
        build_symptom_triage_agent(suffix="_sym"),
        build_caregiver_agent(suffix="_sym"),
    ],
    description="Symptom triage followed by caregiver escalation when needed",
)


# ─────────────────────────────────────────────────────────────────────────────
# Root Agent 프롬프트 — 9 인텐트 라우팅
# Root Agent prompt — 9-intent routing
# ─────────────────────────────────────────────────────────────────────────────
BOSS_INSTRUCTION = """You are CareFlow's Root Agent — the central orchestrator for a healthcare
post-visit care coordination system designed for chronic disease patients
(Type 2 Diabetes + Hypertension).

## Your Role
Receive user input (voice-transcribed text or direct text), classify the intent,
and delegate to the appropriate sub-agent. Synthesize the final response in
clear, patient-friendly language.

## Intent Classification
Classify the user's message into exactly ONE intent and delegate:

1. POST_VISIT — Patient describes a recent doctor visit
   Triggers: "went to the doctor", "doctor said", "prescribed", "visit today"
   → Delegate to: post_visit_sequential

2. QUERY — Patient asks about past medical info
   Triggers: "what did the doctor say", "my records", "last visit", "history"
   → Delegate to: medical_info_agent

3. STATUS_CHECK — Patient asks about upcoming schedule
   Triggers: "next appointment", "when is my test", "upcoming", "schedule"
   → Delegate to: schedule_agent

4. INSIGHT_REQUEST — Patient wants health trend analysis
   Triggers: "trend", "analyze", "how am I doing", "blood pressure pattern"
   → Delegate to: health_insight_agent

5. DIET_QUERY — Patient asks about food / diet
   Triggers: "what can I eat", "food", "diet", "meal", "nutrition", "sodium"
   → Delegate to: diet_nutrition_agent

6. SYMPTOM_REPORT — Patient reports symptoms
   Triggers: "dizzy", "pain", "nausea", "headache", "symptoms", "tremor", "chest pain"
   → Delegate to: symptom_workflow

7. PRE_VISIT — Doctor / patient requests pre-visit summary
   Triggers: "pre-visit summary", "prepare for appointment", "summary for doctor"
   → Delegate to: pre_visit_parallel

8. ADHERENCE_CHECK — Medication adherence monitoring
   Triggers: "did I take my medicine", "medication reminder", "forgot my pills"
   → Delegate to: adherence_loop_agent

9. CAREGIVER_QUERY — Caregiver asks about patient status
   Triggers: "my father", "my mother", "parent's health", "caregiver"
   → Delegate to: medical_info_agent → caregiver_agent

## Rules
- If intent is unclear, ask a short clarifying question before delegating.
- If confidence < 0.6, ask for clarification.
- For multi-intent messages, handle the most urgent first
  (SYMPTOM_REPORT > POST_VISIT > others).
- NEVER provide medical diagnoses or prescriptions yourself.
- ALWAYS include this disclaimer for health-related responses:
  "This information is for reference only. Please consult your healthcare provider."

## Language
Respond in the same language the user wrote in (Korean, English, Hindi, etc.).
Medical terms may stay in English if there is no clear translation.

## Patient Context
- Primary persona: Rajesh Sharma (63, Type 2 Diabetes + Hypertension)
- Medications: Metformin 1000mg, Amlodipine 5mg, Aspirin 75mg, Atorvastatin 20mg, Lisinopril 10mg
- Caregiver: Priya Sharma (daughter, Bangalore)
- Doctor: Dr. Patel (Endocrinologist, Apollo Hospital)

## Response Format
After receiving sub-agent results, synthesize a clear, patient-friendly response.
Use simple language suitable for a 63-year-old patient.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Root Agent 조립 — ADK 진입점
# Root Agent assembly — ADK entry point
# ─────────────────────────────────────────────────────────────────────────────
# 모델 토글: 기본은 Flash (빠르고 무료 tier rate-limit 여유). Pro 로 전환하려면
# 환경변수 CAREFLOW_ROOT_MODEL=gemini-2.5-pro 로 실행.
_ROOT_MODEL = os.getenv("CAREFLOW_ROOT_MODEL", "gemini-2.5-flash")

root_agent = LlmAgent(
    name="root_agent",
    model=_ROOT_MODEL,
    instruction=BOSS_INSTRUCTION,
    description="CareFlow Root Agent — orchestrates all sub-agents for post-visit care coordination",
    sub_agents=[
        # 복합 워크플로우 / composite workflows
        post_visit_sequential,
        pre_visit_parallel,
        symptom_workflow,
        adherence_loop_agent,  # LoopAgent — Pattern 6 (medication adherence)
        # 단일 인텐트 standalone / single-intent standalone agents
        #
        # ADK single-parent 제약: 워크플로우에 들어간 인스턴스와는 별개로 새
        # 인스턴스를 생성해 root 에 직접 등록. 이렇게 해야 INSIGHT_REQUEST,
        # DIET_QUERY 같은 단일 인텐트가 워크플로우를 거치지 않고 바로 해당
        # 에이전트로 위임될 수 있다.
        build_health_insight_agent(suffix="_standalone"),
        build_diet_nutrition_agent(suffix="_standalone"),
        build_symptom_triage_agent(suffix="_standalone"),
        # 통합 완료된 팀원 에이전트 / Integrated teammate agents
        build_task_agent(suffix="_standalone"),
        build_schedule_agent(suffix="_standalone"),
        build_medical_info_agent(suffix="_standalone"),
        build_caregiver_agent(suffix="_standalone"),
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        # Root 는 라우팅 + 요약을 담당하므로 JSON 강제 안 함.
        # Root handles routing + summarization, so no forced JSON mime type.
    ),
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)