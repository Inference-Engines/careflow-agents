"""CareFlow Root Agent — 전체 오케스트레이터 (뼈대 단독 버전).

ADK 진입점. `adk web` 또는 `adk run`으로 실행 시 이 파일의 `root_agent` 변수를
자동으로 로드한다. 현재 커밋은 Somi 담당 서브에이전트 4개 + 안전 레이어만 포함하며,
Task / Medical Info / Schedule / Caregiver 에이전트는 stub 으로 남겨둔다 —
이후 팀원 코드를 ADK 패턴으로 리팩토링해서 해당 stub 을 교체하는 방식으로 통합한다.

Somi's agents (all implemented):
    - health_insight_agent   : trend analysis, proactive insights
    - diet_nutrition_agent   : personalized diet + food-drug interaction
    - symptom_triage_agent   : 3-level urgency classification, safe defaults
    - adherence_loop_agent   : LoopAgent — daily medication monitoring

Teammate agents (stubbed — to be replaced during integration):
    - task_agent         (thatengineerguy)
    - schedule_agent     (Lavanya)
    - medical_info_agent (thatengineerguy)
    - caregiver_agent    (Deeptesha)

ADK single-parent constraint: 모든 워크플로우용 인스턴스는 팩토리로 매번 새로
생성한다. 동일 인스턴스를 여러 parent 아래에 두면 런타임 에러가 난다.

설계 문서 / Design doc: CareFlow_System_Design_EN_somi.md
"""

from __future__ import annotations

import os

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

# Deeptesha 담당 에이전트 — feature/caregiver-agent 브랜치에서 통합
# Deeptesha's agent — integrated on feature/caregiver-agent branch
from careflow.agents.caregiver.agent import build_caregiver_agent

# 안전 레이어 콜백 — 모든 에이전트에 일관 적용
# Safety layer callbacks — applied uniformly across agents
from careflow.agents.safety.plugin import before_model_callback, after_model_callback


# ─────────────────────────────────────────────────────────────────────────────
# 팀원 에이전트 Mock 팩토리 — 통합 시점에 실제 구현으로 교체
# Teammate agent mock factories — to be replaced with real implementations
# ─────────────────────────────────────────────────────────────────────────────
# ADK 는 인스턴스마다 단일 parent 만 허용하므로, 여러 워크플로우에 동일 역할의
# 에이전트를 넣을 때는 매 호출마다 새 LlmAgent 인스턴스를 만들어야 한다.
# Since ADK enforces one parent per agent instance, we return a fresh LlmAgent
# on every call so each workflow (and root standalone) gets its own object.

_TASK_MOCK_INSTRUCTION = """\
You extract medications and tasks from post-visit doctor input and return realistic structured JSON.
Always respond with a JSON object like this (adapt values to the user's message):

{
  "medications": [
    {"name": "Metformin", "dosage": "1000mg", "frequency": "twice daily",
     "timing": "with meals", "status": "modified", "previous_dosage": "500mg"},
    {"name": "Amlodipine", "dosage": "5mg", "frequency": "once daily", "status": "active"}
  ],
  "tasks": [
    {"description": "HbA1c blood test", "due_date": "2026-04-20",
     "priority": "high", "notes": "fasting required"}
  ],
  "safety_check": "passed"
}

Return JSON only, no additional commentary.
"""

_MEDICAL_INFO_MOCK_INSTRUCTION = """\
You are a medical records retrieval agent. Return realistic structured summaries
based on the patient query. For any query, return a believable JSON like:

{
  "summary": "Patient Rajesh Sharma (63, DM2+HTN). Last visit 2026-03-15. BP 140/90, HbA1c 7.2%. Prescribed Metformin 1000mg twice daily.",
  "relevant_records": [
    "Visit 2026-03-15: BP elevated, advised sodium restriction",
    "Visit 2026-02-15: HbA1c 7.5%, started Amlodipine"
  ],
  "source": "visit_records (mock — to be replaced with AlloyDB + pgvector during integration)"
}

Return JSON only, no additional commentary.
"""

_SCHEDULE_MOCK_INSTRUCTION = """\
You manage calendar events and appointment booking. Return realistic JSON for any
scheduling-related query, for example:

{
  "appointments": [
    {"title": "HbA1c Blood Test", "date": "2026-04-20", "time": "08:00",
     "location": "Apollo Hospital Lab", "fasting_required": true},
    {"title": "Follow-up with Dr. Patel", "date": "2026-07-03", "time": "10:00"}
  ],
  "reminders_set": true,
  "conflicts": []
}

Return JSON only, no additional commentary.
"""

# Caregiver mock instruction 제거됨 — Deeptesha 담당 실제 에이전트로 교체.
# build_caregiver_agent 팩토리를 직접 호출해 각 워크플로우에 인스턴스 주입.
# Caregiver mock removed — replaced with Deeptesha's real agent.
# build_caregiver_agent factory is called directly per workflow.


def _make_task_stub(suffix: str = "") -> LlmAgent:
    return LlmAgent(
        name=f"task_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=_TASK_MOCK_INSTRUCTION,
        description="Extracts medications, tasks, and follow-ups from post-visit input (mock — pending integration)",
        output_key="task_result",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )


def _make_medical_info_stub(suffix: str = "") -> LlmAgent:
    return LlmAgent(
        name=f"medical_info_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=_MEDICAL_INFO_MOCK_INSTRUCTION,
        description="Structures visit records and performs RAG search (mock — pending integration)",
        output_key="medical_info_result",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )


def _make_schedule_stub(suffix: str = "") -> LlmAgent:
    return LlmAgent(
        name=f"schedule_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=_SCHEDULE_MOCK_INSTRUCTION,
        description="Manages calendar events and appointment booking (mock — pending integration)",
        output_key="schedule_result",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )


# Caregiver stub 제거됨 — Deeptesha 담당 실제 에이전트를 build_caregiver_agent 로 직접 호출.
# Caregiver stub removed — Deeptesha's real agent is wired via build_caregiver_agent.


# ─────────────────────────────────────────────────────────────────────────────
# 워크플로우 정의 — Sequential / Parallel / Loop 조합
# Workflow definitions — Sequential / Parallel / Loop composition
# ─────────────────────────────────────────────────────────────────────────────

# POST_VISIT: [Task ∥ Schedule] → Medical Info → Diet → Caregiver
# 병렬로 추출하고 순차적으로 후처리하는 전형적인 post-visit 파이프라인.
post_visit_parallel = ParallelAgent(
    name="post_visit_parallel",
    sub_agents=[_make_task_stub("_pv"), _make_schedule_stub("_pv")],
    description="Task extraction and schedule booking run in parallel",
)

post_visit_sequential = SequentialAgent(
    name="post_visit_sequential",
    sub_agents=[
        post_visit_parallel,
        _make_medical_info_stub("_pv"),
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
        _make_medical_info_stub("_prev"),
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
        # 팀원 에이전트 mock — 통합 시 실제 구현으로 교체
        # Teammate agent mocks — replaced with real implementations on integration
        _make_task_stub("_standalone"),
        _make_schedule_stub("_standalone"),
        _make_medical_info_stub("_standalone"),
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
