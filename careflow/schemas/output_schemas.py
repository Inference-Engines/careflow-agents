"""
CareFlow Agent Output Schemas
CareFlow 에이전트 출력 스키마

Pydantic v2 models that define the structured output contract for each
CareFlow sub-agent. Every agent MUST return data conforming to these schemas
so the Boss Agent can aggregate results deterministically.

각 CareFlow 서브 에이전트의 구조화된 출력 계약을 정의하는 Pydantic v2 모델.
모든 에이전트는 Boss Agent가 결과를 결정론적으로 집계할 수 있도록
이 스키마에 맞는 데이터를 반환해야 합니다.

Author: CareFlow Team (APAC Architecture Elite Club 10)
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, confloat


# ---------------------------------------------------------------------------
# Enums — 열거형 상수
# ---------------------------------------------------------------------------

class InsightType(str, Enum):
    """Health Insight 유형 / Type of health insight generated."""
    TREND_ALERT = "trend_alert"
    CORRELATION = "correlation"
    PRE_VISIT_SUMMARY = "pre_visit_summary"
    RECOMMENDATION = "recommendation"


class Severity(str, Enum):
    """심각도 수준 / Severity level for insights and warnings."""
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class RecommendationType(str, Enum):
    """식이 추천 유형 / Type of dietary recommendation."""
    SODIUM_RESTRICTION = "sodium_restriction"
    SUGAR_RESTRICTION = "sugar_restriction"
    GENERAL = "general"
    MEAL_PLAN = "meal_plan"


class CulturalAdaptation(str, Enum):
    """문화권 적응 유형 / Cultural locale for food recommendations."""
    INDIAN = "indian"
    KOREAN = "korean"
    GENERAL = "general"


class UrgencyLevel(str, Enum):
    """증상 긴급도 수준 / Symptom urgency classification level.

    Safe-default 원칙: confidence < 0.7 이면 한 단계 상향 조정.
    Safe-default principle: upgrade by one level when confidence < 0.7.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Shared sub-models — 공용 하위 모델
# ---------------------------------------------------------------------------

class DateRange(BaseModel):
    """분석 기간 / Date range for data analysis window."""
    start: date = Field(..., description="분석 시작일 / Analysis start date")
    end: date = Field(..., description="분석 종료일 / Analysis end date")


class HealthMetric(BaseModel):
    """건강 지표 단일 측정치 / A single health metric measurement.

    Examples: blood_pressure_systolic 140 mmHg, fasting_glucose 128 mg/dL
    """
    metric_type: str = Field(
        ...,
        description=(
            "지표 유형 (e.g. blood_pressure_systolic, fasting_glucose, weight, heart_rate) / "
            "Type of health metric"
        ),
    )
    value: float = Field(..., description="측정값 / Measured value")
    unit: str = Field(..., description="단위 (e.g. mmHg, mg/dL, kg, bpm) / Unit of measurement")
    measured_date: date = Field(..., description="측정일 / Date of measurement")


class FoodItem(BaseModel):
    """음식 항목 / A single food item with nutritional metadata.

    영양소 값은 1회 제공량(serving) 기준.
    Nutrient values are per single serving.
    """
    name: str = Field(..., description="음식명 / Food name (locale-appropriate)")
    category: str = Field(
        ...,
        description="식품 카테고리 (e.g. vegetable, grain, protein, dairy, fruit, snack) / Food category",
    )
    sodium_mg: float = Field(..., ge=0, description="나트륨 (mg/serving) / Sodium content in mg")
    sugar_g: float = Field(..., ge=0, description="당류 (g/serving) / Sugar content in grams")
    calories: float = Field(..., ge=0, description="칼로리 (kcal/serving) / Calories per serving")


class MealPlan(BaseModel):
    """일일 식단 계획 / Daily meal plan with breakfast, lunch, and dinner.

    각 식사는 구체적인 메뉴 항목의 리스트.
    Each meal is a list of specific menu items.
    """
    breakfast: list[str] = Field(..., description="아침 메뉴 / Breakfast menu items")
    lunch: list[str] = Field(..., description="점심 메뉴 / Lunch menu items")
    dinner: list[str] = Field(..., description="저녁 메뉴 / Dinner menu items")


class DrugFoodInteraction(BaseModel):
    """약물-음식 상호작용 / A known drug-food interaction warning.

    출처: openFDA Drug Labeling API, DailyMed.
    Source: openFDA Drug Labeling API, DailyMed.
    """
    drug_name: str = Field(..., description="약물명 / Drug name (e.g. Amlodipine)")
    food_name: str = Field(..., description="상호작용 음식 / Food that interacts")
    risk_level: Severity = Field(
        ...,
        description="위험 수준 (info / warning / urgent) / Risk level of interaction",
    )
    description: str = Field(
        ...,
        description="상호작용 설명 / Human-readable description of the interaction and its risks",
    )


class ICD11Code(BaseModel):
    """ICD-11 진단 코드 / ICD-11 diagnostic code reference.

    WHO ICD-11 국제 질병 분류 코드.
    WHO International Classification of Diseases 11th Revision code.
    """
    code: str = Field(..., description="ICD-11 코드 (e.g. MB40.0) / ICD-11 code")
    title: str = Field(..., description="코드 설명 (e.g. Dizziness) / Code title/description")


class EscalationAction(BaseModel):
    """에스컬레이션 행동 계획 / Actions to take based on symptom urgency.

    safe-default: 의심스러우면 항상 상위 에스컬레이션.
    safe-default: when in doubt, always escalate higher.
    """
    notify_caregiver: bool = Field(
        False,
        description="보호자 알림 여부 / Whether to notify the remote caregiver",
    )
    notify_doctor: bool = Field(
        False,
        description="담당 의사 알림 여부 / Whether to notify the attending doctor",
    )
    recommend_er: bool = Field(
        False,
        description="응급실 방문 권고 여부 / Whether to recommend an ER visit",
    )


# ---------------------------------------------------------------------------
# 1. Health Insight Agent Output — 건강 인사이트 에이전트 출력
# ---------------------------------------------------------------------------

class HealthInsightOutput(BaseModel):
    """Health Insight Agent의 구조화된 출력 / Structured output of the Health Insight Agent.

    누적된 환자 건강 데이터를 분석하여 트렌드, 이상 징후, 상관관계를 감지하고
    실행 가능한 건강 인사이트와 진료 전 요약을 생성합니다.

    Analyzes accumulated patient health data to detect trends, anomalies,
    and correlations, then generates actionable health insights and
    pre-visit summaries.

    Trigger conditions:
      - SCHEDULED: 매주 월요일 주간 건강 인사이트 / Weekly Monday health insights
      - THRESHOLD: 혈압 140/90 3회 연속 초과 시 자동 알림 / Auto-alert on 3x BP threshold breach
      - PRE_VISIT: 예약 D-1 진료 전 요약 자동 생성 / Auto pre-visit summary on appointment D-1
      - ON_DEMAND: 환자/보호자/의료진 직접 요청 / Direct request from patient/caregiver/staff
    """

    insight_type: InsightType = Field(
        ...,
        description="인사이트 유형 / Type of insight generated",
    )
    severity: Severity = Field(
        ...,
        description=(
            "심각도 (info: 정상 범위 / warning: 트렌드 우려 / urgent: 임계값 위반) / "
            "Severity level"
        ),
    )
    title: str = Field(
        ...,
        max_length=200,
        description="인사이트 제목 (환자 친화적 언어) / Insight title in patient-friendly language",
    )
    content: str = Field(
        ...,
        description=(
            "상세 분석 내용 / Detailed analysis content including trend direction, "
            "rate of change, and context"
        ),
    )
    metrics: list[HealthMetric] = Field(
        default_factory=list,
        description="관련 건강 지표 목록 / List of health metrics used in the analysis",
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(  # type: ignore[valid-type]
        ...,
        description=(
            "분석 신뢰도 (0.6 미만이면 'Limited data' 주의 문구 추가) / "
            "Confidence score; append caveat if below 0.6"
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "실행 가능한 권고 사항 목록 (절대 특정 약물/용량을 추천하지 않음) / "
            "Actionable recommendations (NEVER recommend specific medications or dosages)"
        ),
    )
    data_range: DateRange = Field(
        ...,
        description="분석에 사용된 데이터 기간 / Date range of data used in the analysis",
    )
    icd11_codes: list[str] = Field(
        default_factory=list,
        description=(
            "관련 ICD-11 코드 (해당되는 경우) / "
            "Relevant ICD-11 codes if applicable (e.g. ['BA00', 'BA01'])"
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "insight_type": "trend_alert",
                    "severity": "warning",
                    "title": "Systolic blood pressure rising over 3 months",
                    "content": (
                        "Systolic BP increased 10 mmHg over 90 days "
                        "(130 -> 135 -> 140). Crossed pre-hypertension threshold."
                    ),
                    "metrics": [
                        {"metric_type": "blood_pressure_systolic", "value": 140, "unit": "mmHg", "date": "2026-04-03"},
                    ],
                    "confidence": 0.88,
                    "recommendations": [
                        "Discuss blood pressure medication adjustment at next visit."
                    ],
                    "data_range": {"start": "2026-01-03", "end": "2026-04-03"},
                    "icd11_codes": ["BA00"],
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# 2. Diet/Nutrition Agent Output — 식이/영양 에이전트 출력
# ---------------------------------------------------------------------------

class DietRecommendationOutput(BaseModel):
    """Diet/Nutrition Agent의 구조화된 출력 / Structured output of the Diet/Nutrition Agent.

    의사의 식이 지시(나트륨 제한 등)를 구체적이고 실행 가능한 식단 계획으로
    변환합니다. 약물-음식 상호작용을 항상 교차 검증합니다.

    Translates doctor's dietary instructions (e.g. "reduce sodium") into
    specific, actionable meal plans. Always cross-checks drug-food interactions.

    Data sources:
      - USDA FoodData Central (영양소 DB / nutrient database)
      - openFDA Drug Labeling API (약물-음식 상호작용 / food-drug interactions)
      - DailyMed (NLM) (약물 라벨 / drug labeling)
      - WHO Healthy Diet Fact Sheet (식이 가이드라인 / dietary guidelines)
    """

    recommendation_type: RecommendationType = Field(
        ...,
        description="추천 유형 / Type of dietary recommendation",
    )
    recommended_foods: list[FoodItem] = Field(
        default_factory=list,
        description="권장 음식 목록 / List of recommended foods with nutritional info",
    )
    avoid_foods: list[FoodItem] = Field(
        default_factory=list,
        description="회피 음식 목록 / List of foods to avoid",
    )
    meal_plan: Optional[MealPlan] = Field(
        None,
        description="일일 식단 계획 (meal_plan 유형일 때 필수) / Daily meal plan (required for meal_plan type)",
    )
    drug_food_interactions: list[DrugFoodInteraction] = Field(
        default_factory=list,
        description=(
            "약물-음식 상호작용 경고 (항상 체크 — 없으면 빈 리스트) / "
            "Drug-food interaction warnings (always checked; empty list if none)"
        ),
    )
    cultural_adaptation: CulturalAdaptation = Field(
        CulturalAdaptation.GENERAL,
        description=(
            "문화권 적응 (indian / korean / general) / "
            "Cultural locale for food names and meal structure"
        ),
    )
    disclaimer: str = Field(
        default=(
            "These dietary suggestions are general guidance based on your conditions "
            "and medications. For a personalized nutrition plan, please consult a "
            "registered dietitian or your healthcare provider."
        ),
        description="의료 면책 조항 (항상 포함) / Medical disclaimer (always included)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recommendation_type": "sodium_restriction",
                    "recommended_foods": [
                        {"name": "Home-cooked dal (no added salt)", "category": "protein", "sodium_mg": 15, "sugar_g": 1.0, "calories": 120},
                    ],
                    "avoid_foods": [
                        {"name": "Pickles (achar)", "category": "condiment", "sodium_mg": 1200, "sugar_g": 2.0, "calories": 30},
                    ],
                    "meal_plan": {
                        "breakfast": ["Oatmeal with banana and cinnamon", "Unsweetened tea"],
                        "lunch": ["Brown rice", "Unsalted moong dal", "Palak sabzi"],
                        "dinner": ["Grilled fish", "Steamed broccoli", "1 roti"],
                    },
                    "drug_food_interactions": [
                        {
                            "drug_name": "Amlodipine",
                            "food_name": "Grapefruit",
                            "risk_level": "warning",
                            "description": "Grapefruit can increase drug concentration and side effects.",
                        },
                    ],
                    "cultural_adaptation": "indian",
                    "disclaimer": (
                        "These dietary suggestions are general guidance based on your conditions "
                        "and medications. For a personalized nutrition plan, please consult a "
                        "registered dietitian or your healthcare provider."
                    ),
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# 3. Symptom Triage Agent Output — 증상 분류 에이전트 출력
# ---------------------------------------------------------------------------

class SymptomTriageOutput(BaseModel):
    """Symptom Triage Agent의 구조화된 출력 / Structured output of the Symptom Triage Agent.

    환자가 보고한 증상을 긴급도별로 분류하고, 약물 및 건강 컨텍스트와
    교차 분석하여 적절한 에스컬레이션 체인을 트리거합니다.

    Classifies patient-reported symptoms by urgency, cross-analyzes with
    medication and health context, and triggers appropriate escalation chains.

    CRITICAL SAFETY PRINCIPLE — safe-default:
      confidence < 0.7 이면 자동으로 긴급도 한 단계 상향.
      If confidence < 0.7, automatically upgrade urgency by one level.
      오탐(false alarm)이 미탐(missed emergency)보다 항상 낫다.
      A false alarm is ALWAYS preferable to a missed emergency.
    """

    reported_symptoms: list[str] = Field(
        ...,
        min_length=1,
        description="환자가 보고한 증상 목록 / List of symptoms reported by the patient",
    )
    urgency_level: UrgencyLevel = Field(
        ...,
        description=(
            "긴급도 수준 (LOW / MEDIUM / HIGH) / Urgency classification level. "
            "safe-default 적용 후 최종 값 / Final value after safe-default adjustment"
        ),
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(  # type: ignore[valid-type]
        ...,
        description=(
            "분류 신뢰도 (0.7 미만이면 긴급도 한 단계 상향) / "
            "Classification confidence; upgrade urgency if below 0.7"
        ),
    )
    icd11_codes: list[ICD11Code] = Field(
        default_factory=list,
        description="관련 ICD-11 코드 / Relevant ICD-11 diagnostic codes for reported symptoms",
    )
    analysis: str = Field(
        ...,
        description=(
            "증상 분석 결과 (약물 상관관계, 비전형 패턴 등 포함) / "
            "Symptom analysis including medication correlation and atypical pattern checks"
        ),
    )
    medication_correlation: Optional[str] = Field(
        None,
        description=(
            "약물 상관관계 분석 (해당 시) / "
            "Medication-symptom correlation analysis if relevant "
            "(e.g. 'Missed 2 Metformin doses — possible blood sugar irregularity')"
        ),
    )
    adherence_correlation: Optional[str] = Field(
        None,
        description=(
            "복약 순응도 상관관계 (해당 시) / "
            "Medication adherence correlation if relevant "
            "(e.g. 'Adherence dropped to 60% this week')"
        ),
    )
    recommendation: str = Field(
        ...,
        description=(
            "환자에게 전달할 권고 사항 (간결하고 실행 가능한 문장) / "
            "Clear, actionable recommendation for the patient"
        ),
    )
    escalation: EscalationAction = Field(
        ...,
        description="에스컬레이션 행동 계획 / Escalation actions based on urgency level",
    )
    safe_default_applied: bool = Field(
        ...,
        description=(
            "safe-default 상향 조정 적용 여부 / "
            "Whether the urgency was upgraded due to confidence < 0.7"
        ),
    )
    disclaimer: str = Field(
        default=(
            "This symptom assessment is for informational purposes only and does not "
            "constitute a medical diagnosis. If you are experiencing a medical emergency, "
            "please call emergency services (112/108) immediately."
        ),
        description="의료 면책 조항 (항상 포함) / Medical disclaimer (always included)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reported_symptoms": ["dizziness", "hand_tremors"],
                    "urgency_level": "MEDIUM",
                    "confidence": 0.82,
                    "icd11_codes": [
                        {"code": "MB40.0", "title": "Dizziness"},
                        {"code": "8A07", "title": "Tremor"},
                    ],
                    "analysis": (
                        "Dizziness and hand tremors correlated with 2 missed "
                        "Metformin doses. Possible blood sugar irregularity."
                    ),
                    "medication_correlation": (
                        "Metformin 1000mg — 2 missed doses in last 3 days. "
                        "Possible blood sugar fluctuation."
                    ),
                    "adherence_correlation": "Adherence dropped to 78% this week.",
                    "recommendation": (
                        "Measure blood sugar immediately. Have a small snack. "
                        "If symptoms persist beyond 2 hours, visit the hospital."
                    ),
                    "escalation": {
                        "notify_caregiver": True,
                        "notify_doctor": False,
                        "recommend_er": False,
                    },
                    "safe_default_applied": False,
                    "disclaimer": (
                        "This symptom assessment is for informational purposes only "
                        "and does not constitute a medical diagnosis. If you are "
                        "experiencing a medical emergency, please call emergency "
                        "services (112/108) immediately."
                    ),
                }
            ]
        }
    }
