"""
Medication Adherence LoopAgent — 약물 순응도 모니터
Medication Adherence Monitor using ADK LoopAgent pattern.

설계 문서 Pattern 6 구현:
  LoopAgent가 sub_agents를 반복 실행하여 약물 순응도를 모니터링한다.
  The LoopAgent repeatedly executes sub_agents to monitor medication adherence.

Architecture / 아키텍처:
  LoopAgent (max_iterations=5)
    ├── check_agent (LlmAgent) — 복용 시간/순응도 확인
    │   Step 1: 약물 복용 시간 확인 / Check medication schedule
    │   Step 2: 순응도 확인 → 복용=로그 / 미복용=리마인더
    └── remind_agent (LlmAgent) — 리마인더/에스컬레이션 전송
        Step 3: 2회 연속 미복용 → 보호자 에스컬레이션

Safety / 안전:
  - before_model_callback, after_model_callback 연결
  - cross-patient 접근 차단은 SafetyPlugin에서 처리
"""

from google.adk.agents import LoopAgent, LlmAgent
from google.genai import types

from careflow.agents.adherence_loop.tools import (
    check_medication_time,
    check_adherence,
    send_reminder,
)
# 안전 콜백 임포트 — 모든 LlmAgent에 적용
# Safety callbacks — applied to all LlmAgents
from careflow.agents.safety.plugin import (
    before_model_callback,
    after_model_callback,
)


# =============================================================================
# Sub-Agent 1: 복용 확인 에이전트 / Medication Check Agent
# =============================================================================
#
# 역할: 환자의 현재 복용 예정 약물을 확인하고, 각 약물의 복용 여부를 체크
# Role: Check patient's due medications and verify adherence for each
#
# output_key를 통해 결과를 세션 상태에 저장 → remind_agent가 참조
# Results saved to session state via output_key → referenced by remind_agent

CHECK_AGENT_INSTRUCTION = """You are the Medication Check Agent in CareFlow's adherence monitoring loop.

## Your Role / 역할
1. Call `check_medication_time` to find which medications are currently due.
2. For each due medication, call `check_adherence` to verify if it has been taken.
3. Compile results into a structured JSON report.

## Output Format / 출력 형식
Return JSON with this schema:
{
  "patient_id": "string",
  "check_slot": "morning|evening|null",
  "medications_checked": [
    {
      "name": "string",
      "dosage": "string",
      "taken": true|false,
      "consecutive_misses": 0,
      "needs_escalation": false
    }
  ],
  "any_missed": true|false,
  "needs_caregiver_alert": true|false
}

## Rules / 규칙
- Use patient_id from the session state (state["current_patient_id"]) or default "P001".
- If no medications are due (null slot), return empty medications_checked array.
- Set needs_caregiver_alert=true if ANY medication has consecutive_misses >= 2.
"""

check_agent = LlmAgent(
    name="adherence_check_agent",
    model="gemini-2.5-flash",
    instruction=CHECK_AGENT_INSTRUCTION,
    tools=[check_medication_time, check_adherence],
    output_key="adherence_check_result",
    description=(
        "Checks medication schedule and verifies adherence status "
        "for each due medication"
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,  # 순응도 확인은 deterministic / Deterministic for adherence checks
    ),
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)


# =============================================================================
# Sub-Agent 2: 리마인더 에이전트 / Reminder Agent
# =============================================================================
#
# 역할: check_agent의 결과를 기반으로 리마인더 또는 에스컬레이션 실행
# Role: Based on check_agent results, send reminders or escalate
#
# adherence_check_result를 세션 상태에서 읽어 판단
# Reads adherence_check_result from session state

REMIND_AGENT_INSTRUCTION = """You are the Medication Reminder Agent in CareFlow's adherence monitoring loop.

## Your Role / 역할
Read the adherence check results from state["adherence_check_result"] and take action:

1. **Medication taken** → Log confirmation (no action needed, just acknowledge).
2. **Medication missed (consecutive_misses < 2)** → Call `send_reminder` with reminder_type="patient".
3. **Medication missed (consecutive_misses >= 2)** → Call `send_reminder` with reminder_type="caregiver"
   for caregiver escalation (보호자 에스컬레이션).

## Output Format / 출력 형식
Return JSON:
{
  "actions_taken": [
    {
      "medication_name": "string",
      "action": "logged|reminded|escalated",
      "reminder_type": "patient|caregiver|none",
      "status": "sent|skipped"
    }
  ],
  "total_reminders_sent": 0,
  "total_escalations": 0,
  "loop_should_continue": true|false
}

## Rules / 규칙
- Set loop_should_continue=false if all medications are taken or escalations have been sent.
- Set loop_should_continue=true if there are still pending reminders to retry.
- Use patient_id from state or default "P001".
"""

remind_agent = LlmAgent(
    name="adherence_remind_agent",
    model="gemini-2.5-flash",
    instruction=REMIND_AGENT_INSTRUCTION,
    tools=[send_reminder],
    output_key="adherence_remind_result",
    description=(
        "Sends medication reminders to patient or escalates to "
        "caregiver after consecutive misses"
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,  # 리마인더 로직은 deterministic / Deterministic for reminder logic
    ),
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)


# =============================================================================
# LoopAgent 조립 — 약물 순응도 모니터 / Medication Adherence Monitor
# =============================================================================
#
# ADK LoopAgent 패턴:
#   sub_agents를 순서대로 반복 실행 (check → remind → check → remind → ...)
#   max_iterations로 무한 루프 방지
#
# max_iterations=5 설정 근거:
#   - 일반적으로 1-2회 반복이면 충분 (확인 → 리마인더 → 재확인)
#   - 5회는 안전 마진 — 네트워크 지연, 환자 응답 대기 고려
#   - 5회 초과 시 강제 종료 → 보호자에게 수동 확인 요청
#
# max_iterations=5 rationale:
#   - Typically 1-2 iterations suffice (check → remind → re-check)
#   - 5 is a safety margin for network delays and patient response time
#   - Beyond 5 → force stop and request manual caregiver check

adherence_loop_agent = LoopAgent(
    name="adherence_loop_agent",
    sub_agents=[check_agent, remind_agent],
    max_iterations=5,
    description=(
        "Medication adherence monitoring loop: checks medication schedule, "
        "verifies adherence, sends reminders, and escalates to caregiver "
        "after 2 consecutive misses (Pattern 6)"
    ),
)
