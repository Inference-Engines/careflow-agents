"""
Diet/Nutrition Agent — LlmAgent Assembly
식이/영양 에이전트 — LlmAgent 조립

Assembles the Diet/Nutrition Agent using Google ADK LlmAgent pattern.
환자의 질환·복용 약물·의사 지시 기반 개인화된 식이 추천을 생성합니다.

Generates personalized diet recommendations based on the patient's
conditions, medications, and doctor's dietary instructions.
"""

from google.adk.agents import LlmAgent
# Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
# Gemini API constraint: google_search cannot be combined with FunctionTools
# ("Multiple tools are supported only when they are all search tools")
# from google.adk.tools.google_search_tool import google_search
from google.genai import types

from careflow.agents.diet_nutrition.prompt import DIET_NUTRITION_INSTRUCTION
from careflow.agents.diet_nutrition.tools import (
    check_food_drug_interaction,
    get_dietary_restrictions,
    get_patient_medications,
    lookup_food_nutrition,
)
# 안전 콜백 임포트 — 프롬프트 인젝션 차단, PII 마스킹, 의료 면책조항 삽입
# Safety callbacks — prompt injection blocking, PII masking, medical disclaimer injection
from careflow.agents.safety.plugin import (
    before_model_callback,
    after_model_callback,
)

# ---------------------------------------------------------------------------
# Agent Configuration — 에이전트 설정
# ---------------------------------------------------------------------------
# temperature 0.4: 사실 기반 응답이 중요하지만 약간의 창의성 허용 (식단 제안)
# temperature 0.4: factual accuracy is key, but allow some creativity for meal suggestions
#
# response_mime_type="application/json": 구조화된 JSON 출력 강제
# response_mime_type="application/json": enforce structured JSON output
#
# output_key: 다운스트림 에이전트(예: caregiver_notification_agent)가
#             세션 상태에서 이 키로 결과를 참조할 수 있음
# output_key: downstream agents (e.g., caregiver_notification_agent)
#             can reference this result from session state
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Factory function — ADK single-parent 제약 대응
# Factory function — work around ADK single-parent constraint
#
# 동일 에이전트를 여러 워크플로우 + root standalone에 등록하려면 매번 새
# 인스턴스를 만들어야 함. suffix로 name 충돌 방지.
# A fresh instance is required to register the same agent under multiple
# parents; suffix prevents name collisions.
# ---------------------------------------------------------------------------
def build_diet_nutrition_agent(suffix: str = "") -> LlmAgent:
    """Diet/Nutrition Agent 인스턴스 생성 / Build a new Diet/Nutrition Agent."""
    return LlmAgent(
        name=f"diet_nutrition_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=DIET_NUTRITION_INSTRUCTION,
        tools=[
            get_patient_medications,
            get_dietary_restrictions,
            lookup_food_nutrition,
            check_food_drug_interaction,
            # Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
            # Gemini API constraint: google_search cannot coexist with FunctionTools
            # ("Multiple tools are supported only when they are all search tools")
            # google_search,
        ],
        output_key="diet_recommendation_result",
        description=(
            "Generates personalized diet recommendations based on "
            "conditions and medications"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type="application/json",
        ),
        # 안전 콜백 연결 — 입력/출력 양방향 보호
        # Safety callbacks — bidirectional input/output protection
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
    )


# Backward-compat default export / 기존 임포트 호환용 기본 인스턴스
diet_nutrition_agent = build_diet_nutrition_agent()
