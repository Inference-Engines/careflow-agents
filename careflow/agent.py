"""CareFlow Root Agent — 멀티에이전트 오케스트레이터 / Multi-Agent Orchestrator.

Google ADK 기반 멀티에이전트 아키텍처. 루트 LlmAgent가 9가지 인텐트를 분류하고,
SequentialAgent·ParallelAgent·LoopAgent 조합으로 임상 워크플로우를 실행한다.
ADK 진입점: `adk web` 또는 `adk run` 실행 시 이 모듈의 `root_agent`를 자동 로드.

Multi-agent architecture built on Google ADK. A root LlmAgent classifies
9 patient intents and delegates to composite workflows (Sequential, Parallel,
Loop) that mirror real clinical care coordination patterns.

Sub-agents (8 total, each with dedicated Google Cloud integration):
    ┌─ health_insight_agent   : 건강 추세 분석 / AlloyDB time-series trends
    ├─ diet_nutrition_agent   : 식이 관리 / personalized diet + food-drug interaction
    ├─ symptom_triage_agent   : 증상 분류 / 3-level urgency (Red/Yellow/Green)
    ├─ adherence_loop_agent   : 복약 모니터링 / LoopAgent — daily med adherence
    ├─ task_agent             : 처방 추출 / medication extraction + openFDA DDI
    ├─ schedule_agent         : 일정 관리 / Google Calendar MCP integration
    ├─ medical_info_agent     : 의료 정보 검색 / Agentic RAG (HyDE+RRF+Self-RAG)
    └─ caregiver_agent        : 보호자 알림 / Gmail MCP notifications

ADK single-parent 제약: 팩토리 패턴으로 워크플로우마다 새 인스턴스 생성.
ADK single-parent constraint: factory pattern creates fresh instances per workflow.
"""

from __future__ import annotations

# ── Rate Limiter — 429 방어 / 429 RESOURCE_EXHAUSTED Protection ─────────────
# genai Client 생성 전에 임포트해야 자동으로 retry + exponential backoff 적용됨.
# Must be imported before any genai Client — auto-patches with retry logic.
import careflow.rate_limiter  # noqa: F401

import os
from datetime import datetime

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


# ── 워크플로우 정의 / Workflow Definitions ───────────────────────────────────
# ADK의 Sequential·Parallel·Loop 패턴을 조합하여 임상 워크플로우를 구현.
# Composite ADK patterns (Sequential / Parallel / Loop) model clinical workflows.

# ── 포스트-비짓 워크플로우 / Post-Visit Workflow ──────────────────────────────
# ParallelAgent로 Task+Schedule을 동시 실행 후, SequentialAgent로
# MedicalInfo→Diet→Caregiver 순차 처리. 실제 임상 사후관리 흐름을 반영.
# Parallel extraction (Task+Schedule), then sequential enrichment
# (MedicalInfo→Diet→Caregiver) mirrors real clinical post-visit flow.
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

# ── 사전-방문 워크플로우 / Pre-Visit Workflow ─────────────────────────────────
# 건강 추세 + 의료 기록을 병렬 조회하여 의사에게 사전 요약 제공.
# Parallel fetch of health trends + medical records for pre-visit briefing.
pre_visit_parallel = ParallelAgent(
    name="pre_visit_parallel",
    sub_agents=[
        build_health_insight_agent(suffix="_prev"),
        build_medical_info_agent(suffix="_prev"),
    ],
    description="Health insight analysis and medical records retrieval in parallel",
)

# ── 증상 보고 워크플로우 / Symptom Report Workflow ────────────────────────────
# 증상 분류 후 위험도가 높으면 보호자에게 자동 에스컬레이션 (SequentialAgent).
# Triage first, then auto-escalate to caregiver if urgency is Red/Yellow.
symptom_workflow = SequentialAgent(
    name="symptom_workflow",
    sub_agents=[
        build_symptom_triage_agent(suffix="_sym"),
        build_caregiver_agent(suffix="_sym"),
    ],
    description="Symptom triage followed by caregiver escalation when needed",
)


# ── 루트 에이전트 프롬프트 — 9가지 인텐트 라우팅 / Root Prompt — 9-Intent Router ──
# 환자 메시지를 9가지 인텐트로 분류하고, 적합한 서브에이전트/워크플로우에 위임.
# Classifies patient messages into 9 intents and delegates to the right sub-agent.
# 인텐트 우선순위: SYMPTOM_REPORT > POST_VISIT > 나머지 (환자 안전 최우선)
# Intent priority: SYMPTOM_REPORT > POST_VISIT > others (patient safety first).
BOSS_INSTRUCTION = """You are CareFlow's Root Agent — the central orchestrator for a healthcare
post-visit care coordination system designed for chronic disease patients
(Type 2 Diabetes + Hypertension).

## Your Role
Receive user input (voice-transcribed text or direct text), classify the intent,
and delegate to the appropriate sub-agent. Synthesize the final response in
clear, patient-friendly language.

Today's date: {current_date} ({current_weekday}). Use this as reference for all date calculations.

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
- The safety layer will automatically add disclaimers when needed.


## Language
Respond in English only, regardless of user's language.
Medical terms should also be in English.

## Patient Context
- Primary persona: Rajesh Sharma (63, Type 2 Diabetes + Hypertension)
- Medications: Metformin 1000mg, Amlodipine 5mg, Aspirin 75mg, Atorvastatin 20mg, Lisinopril 10mg
- Caregiver: Priya Sharma (daughter, Bangalore)
- Doctor: Dr. Patel (Endocrinologist, Apollo Hospital)

## Response Format
After receiving sub-agent results, synthesize a clear, patient-friendly response.
Use simple language suitable for a 63-year-old patient.
"""


# ── 루트 에이전트 조립 — ADK 진입점 / Root Agent Assembly — ADK Entry Point ───
# 모델 토글: Flash가 기본 (빠르고 무료 Tier 여유). Pro는 환경변수로 전환.
# Model toggle: Flash default (fast + free-tier friendly). Set
# CAREFLOW_ROOT_MODEL=gemini-2.5-pro to switch.
_ROOT_MODEL = os.getenv("CAREFLOW_ROOT_MODEL", "gemini-2.5-flash")

# 동적 날짜 주입 — LLM이 "오늘"을 올바르게 인식하도록 프롬프트에 삽입.
# Dynamic date injection — so the LLM can reason about "today" correctly.
_now = datetime.now()
_BOSS_INSTRUCTION_FORMATTED = BOSS_INSTRUCTION.format(
    current_date=_now.strftime("%Y-%m-%d"),
    current_weekday=_now.strftime("%A"),
)

root_agent = LlmAgent(
    name="root_agent",
    model=_ROOT_MODEL,
    instruction=_BOSS_INSTRUCTION_FORMATTED,
    description="CareFlow Root Agent — orchestrates all sub-agents for post-visit care coordination",
    sub_agents=[
        # ── 복합 워크플로우 / Composite Workflows ────────────────────────
        post_visit_sequential,    # POST_VISIT 인텐트 → 5단계 파이프라인
        pre_visit_parallel,       # PRE_VISIT 인텐트 → 병렬 사전 요약
        symptom_workflow,         # SYMPTOM_REPORT 인텐트 → 분류 + 에스컬레이션
        adherence_loop_agent,     # ADHERENCE_CHECK → LoopAgent 반복 확인
        # ── 독립 에이전트 / Standalone Agents ────────────────────────────
        # ADK single-parent 제약으로 워크플로우용과 별도 인스턴스 필요.
        # Fresh instances (factory pattern) avoid ADK single-parent violation.
        build_health_insight_agent(suffix="_standalone"),
        build_diet_nutrition_agent(suffix="_standalone"),
        build_symptom_triage_agent(suffix="_standalone"),
        build_task_agent(suffix="_standalone"),
        build_schedule_agent(suffix="_standalone"),
        build_medical_info_agent(suffix="_standalone"),
        build_caregiver_agent(suffix="_standalone"),
    ],
    # temperature 0.3: 라우팅 정확도를 위해 낮게, 요약 자연스러움 유지.
    # Low temperature for routing accuracy while keeping summaries natural.
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)