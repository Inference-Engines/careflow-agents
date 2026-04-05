# Copyright 2026 CareFlow Team
#
# CareFlow 결정론적 가드레일 — LLM이 절대 오버라이드할 수 없는 하드코딩 규칙
# Deterministic guardrails — hardcoded rules that CANNOT be overridden by LLM.
#
# 설계 문서 참조 / Design doc reference:
#   CareFlow_System_Design_EN_somi.md — Section 3-10, Layer 6 (Deterministic Rules)
#
# 핵심 원칙 / Core principle:
#   이 모듈의 규칙은 LLM 출력과 무관하게 항상 적용된다.
#   Rules in this module are ALWAYS enforced regardless of LLM output.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# 열거형 & 데이터 클래스 / Enums & Dataclasses
# =============================================================================

class UrgencyLevel(str, Enum):
    """긴급도 수준 / Urgency level for symptom triage."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


@dataclass
class DosageRange:
    """약물 용량 범위 정의 / Drug dosage range definition.

    Attributes:
        drug_name: 약물명 (소문자 정규화) / drug name (lowercased)
        min_mg_per_day: 일일 최소 용량(mg) / minimum daily dose in mg
        max_mg_per_day: 일일 최대 용량(mg) / maximum daily dose in mg
        unit: 용량 단위 / dosage unit
        notes: 참고사항 / additional notes
    """
    drug_name: str
    min_mg_per_day: float
    max_mg_per_day: float
    unit: str = "mg/day"
    notes: str = ""


@dataclass
class GuardrailResult:
    """가드레일 검증 결과 / Guardrail validation result.

    Attributes:
        passed: 검증 통과 여부 / whether validation passed
        violations: 위반 목록 / list of violations
        warnings: 경고 목록 / list of warnings
        modified_data: 수정된 데이터 (자동 상향 등) / modified data (e.g., auto-escalation)
    """
    passed: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    modified_data: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 약물 용량 데이터베이스 / Drug Dosage Database
#   실무에서는 DB나 외부 API에서 가져오겠지만, MVP에서는 하드코딩한다.
#   In production, this would come from a DB or API; hardcoded for MVP.
# =============================================================================

DOSAGE_DATABASE: dict[str, DosageRange] = {
    "metformin": DosageRange(
        drug_name="metformin",
        min_mg_per_day=500,
        max_mg_per_day=2550,
        notes="Type 2 diabetes; 위장장애 시 감량 / reduce if GI issues",
    ),
    "insulin glargine": DosageRange(
        drug_name="insulin glargine",
        min_mg_per_day=10,   # 10 units
        max_mg_per_day=80,   # 80 units
        unit="units/day",
        notes="Basal insulin; 개인차 큼 / highly individualized",
    ),
    "atorvastatin": DosageRange(
        drug_name="atorvastatin",
        min_mg_per_day=10,
        max_mg_per_day=80,
        notes="Cholesterol; 간기능 모니터링 필요 / monitor liver function",
    ),
    "amlodipine": DosageRange(
        drug_name="amlodipine",
        min_mg_per_day=2.5,
        max_mg_per_day=10,
        notes="Hypertension; 노인은 2.5mg부터 / start 2.5mg in elderly",
    ),
    "aspirin": DosageRange(
        drug_name="aspirin",
        min_mg_per_day=75,
        max_mg_per_day=325,
        notes="Cardiac; 위장 출혈 주의 / GI bleed risk",
    ),
    "paracetamol": DosageRange(
        drug_name="paracetamol",
        min_mg_per_day=500,
        max_mg_per_day=4000,
        notes="해열진통; 간독성 주의 / hepatotoxicity risk above max",
    ),
    "losartan": DosageRange(
        drug_name="losartan",
        min_mg_per_day=25,
        max_mg_per_day=100,
        notes="ARB for hypertension; 신기능 모니터링 / monitor renal function",
    ),
    "glimepiride": DosageRange(
        drug_name="glimepiride",
        min_mg_per_day=1,
        max_mg_per_day=8,
        notes="Sulfonylurea; 저혈당 주의 / hypoglycemia risk",
    ),
}


# =============================================================================
# 알레르기 위험 식품 매핑 / Allergy-Risk Food Mapping
#   알레르기 → 차단해야 할 식품 목록
#   allergy → list of foods to block
# =============================================================================

ALLERGY_FOOD_MAP: dict[str, list[str]] = {
    "peanut": [
        "peanut", "groundnut", "peanut butter", "satay",
        "땅콩", "땅콩버터",
    ],
    "shellfish": [
        "shrimp", "prawn", "crab", "lobster", "oyster", "clam", "mussel",
        "새우", "게", "굴", "조개",
    ],
    "dairy": [
        "milk", "cheese", "butter", "cream", "yogurt", "paneer", "ghee",
        "우유", "치즈", "버터", "요거트",
    ],
    "gluten": [
        "wheat", "barley", "rye", "bread", "pasta", "naan", "roti", "chapati",
        "밀", "보리", "빵", "파스타",
    ],
    "egg": [
        "egg", "mayonnaise", "meringue",
        "계란", "달걀", "마요네즈",
    ],
    "soy": [
        "soy", "soybean", "tofu", "tempeh", "edamame", "soy sauce",
        "두부", "콩", "간장",
    ],
    "tree_nut": [
        "almond", "cashew", "walnut", "pistachio", "pecan", "macadamia",
        "아몬드", "호두", "캐슈넛",
    ],
}


# =============================================================================
# 위험 증상 키워드 — 자동 HIGH 상향 트리거
# Critical symptom keywords — auto-escalate to HIGH urgency
# =============================================================================

CRITICAL_SYMPTOM_KEYWORDS: dict[str, UrgencyLevel] = {
    # ── EMERGENCY 수준 — 즉시 119 / Immediate emergency ──
    "chest_pain": UrgencyLevel.EMERGENCY,
    "chest pain": UrgencyLevel.EMERGENCY,
    "heart attack": UrgencyLevel.EMERGENCY,
    "cardiac arrest": UrgencyLevel.EMERGENCY,
    "stroke": UrgencyLevel.EMERGENCY,
    "seizure": UrgencyLevel.EMERGENCY,
    "unconscious": UrgencyLevel.EMERGENCY,
    "not breathing": UrgencyLevel.EMERGENCY,
    "severe bleeding": UrgencyLevel.EMERGENCY,
    "anaphylaxis": UrgencyLevel.EMERGENCY,
    "흉통": UrgencyLevel.EMERGENCY,
    "심장마비": UrgencyLevel.EMERGENCY,
    "의식불명": UrgencyLevel.EMERGENCY,

    # ── HIGH 수준 — 빠른 의료 상담 필요 / Needs prompt medical attention ──
    "breathing_difficulty": UrgencyLevel.HIGH,
    "breathing difficulty": UrgencyLevel.HIGH,
    "shortness of breath": UrgencyLevel.HIGH,
    "high fever": UrgencyLevel.HIGH,
    "severe headache": UrgencyLevel.HIGH,
    "blood in stool": UrgencyLevel.HIGH,
    "blood in urine": UrgencyLevel.HIGH,
    "sudden vision loss": UrgencyLevel.HIGH,
    "severe abdominal pain": UrgencyLevel.HIGH,
    "fainting": UrgencyLevel.HIGH,
    "suicidal": UrgencyLevel.HIGH,
    "self harm": UrgencyLevel.HIGH,
    "호흡곤란": UrgencyLevel.HIGH,
    "고열": UrgencyLevel.HIGH,
    "혈변": UrgencyLevel.HIGH,
    "실신": UrgencyLevel.HIGH,
}


# =============================================================================
# 가드레일 함수 / Guardrail Functions
# =============================================================================

def validate_dosage(
    drug_name: str,
    proposed_mg_per_day: float,
) -> GuardrailResult:
    """약물 용량 범위를 검증한다 / Validate drug dosage against safe range.

    약물명이 DB에 없으면 경고만 발생시키고 통과시킨다.
    If drug is not in DB, emit a warning and pass through.

    Args:
        drug_name: 약물명 / drug name
        proposed_mg_per_day: 제안 일일 용량(mg) / proposed daily dose in mg

    Returns:
        GuardrailResult: 검증 결과 / validation result
    """
    result = GuardrailResult()
    normalized = drug_name.strip().lower()

    if normalized not in DOSAGE_DATABASE:
        result.warnings.append(
            f"Drug '{drug_name}' not found in dosage DB — "
            f"cannot validate. Manual review recommended. "
            f"(약물 '{drug_name}'이(가) DB에 없어 검증 불가)"
        )
        return result

    dosage = DOSAGE_DATABASE[normalized]

    if proposed_mg_per_day > dosage.max_mg_per_day:
        result.passed = False
        result.violations.append(
            f"⛔ BLOCKED: {drug_name} {proposed_mg_per_day}{dosage.unit} exceeds "
            f"maximum safe dose ({dosage.max_mg_per_day}{dosage.unit}). "
            f"(최대 안전 용량 초과)"
        )
        logger.error(
            "[Guardrail] Dosage violation: %s %.1f > max %.1f",
            drug_name, proposed_mg_per_day, dosage.max_mg_per_day,
        )

    elif proposed_mg_per_day < dosage.min_mg_per_day:
        result.passed = False
        result.violations.append(
            f"⚠️ WARNING: {drug_name} {proposed_mg_per_day}{dosage.unit} below "
            f"minimum therapeutic dose ({dosage.min_mg_per_day}{dosage.unit}). "
            f"(최소 치료 용량 미달)"
        )
        logger.warning(
            "[Guardrail] Dosage below minimum: %s %.1f < min %.1f",
            drug_name, proposed_mg_per_day, dosage.min_mg_per_day,
        )

    else:
        logger.debug(
            "[Guardrail] Dosage OK: %s %.1f within [%.1f, %.1f]",
            drug_name, proposed_mg_per_day,
            dosage.min_mg_per_day, dosage.max_mg_per_day,
        )

    return result


def check_allergy_food_conflict(
    patient_allergies: list[str],
    recommended_foods: list[str],
) -> GuardrailResult:
    """알레르기 위험 식품을 차단한다 / Block allergy-risk foods.

    환자의 알레르기 목록과 추천 식품 목록을 교차 검증한다.
    Cross-validates patient allergies against recommended food list.

    Args:
        patient_allergies: 환자 알레르기 목록 / patient allergy list (e.g., ["peanut", "dairy"])
        recommended_foods: 추천 식품 목록 / recommended food list (e.g., ["paneer tikka", "salad"])

    Returns:
        GuardrailResult: 위반 식품이 있으면 passed=False / passed=False if conflict found
    """
    result = GuardrailResult()
    normalized_allergies = [a.strip().lower() for a in patient_allergies]

    for allergy in normalized_allergies:
        if allergy not in ALLERGY_FOOD_MAP:
            result.warnings.append(
                f"Allergy '{allergy}' not in mapping DB — "
                f"cannot auto-check. (알레르기 '{allergy}' DB에 없음)"
            )
            continue

        blocked_foods = ALLERGY_FOOD_MAP[allergy]
        for food in recommended_foods:
            food_lower = food.strip().lower()
            for blocked in blocked_foods:
                if blocked.lower() in food_lower:
                    result.passed = False
                    result.violations.append(
                        f"⛔ BLOCKED: '{food}' contains allergen '{allergy}' "
                        f"(matched: '{blocked}'). "
                        f"(알레르기 위험: '{food}'에 '{allergy}' 성분 포함)"
                    )
                    logger.error(
                        "[Guardrail] Allergy conflict: food='%s', allergen='%s', matched='%s'",
                        food, allergy, blocked,
                    )

    return result


def escalate_by_symptoms(
    reported_symptoms: list[str],
    current_urgency: UrgencyLevel = UrgencyLevel.LOW,
) -> GuardrailResult:
    """위험 증상 키워드에 따라 긴급도를 자동 상향한다.
    Auto-escalate urgency level based on critical symptom keywords.

    규칙: 증상 키워드가 현재 긴급도보다 높은 수준에 매핑되면 자동 상향.
    Rule: if symptom keyword maps to a higher urgency than current, auto-escalate.

    Args:
        reported_symptoms: 보고된 증상 목록 / list of reported symptoms
        current_urgency: 현재 긴급도 / current urgency level

    Returns:
        GuardrailResult: modified_data["urgency"]에 최종 긴급도 포함
                         modified_data["urgency"] contains final urgency level
    """
    result = GuardrailResult()

    # 긴급도 순서 정의 / urgency ordering
    urgency_order = {
        UrgencyLevel.LOW: 0,
        UrgencyLevel.MEDIUM: 1,
        UrgencyLevel.HIGH: 2,
        UrgencyLevel.EMERGENCY: 3,
    }

    max_urgency = current_urgency

    for symptom in reported_symptoms:
        symptom_lower = symptom.strip().lower()

        # 정확한 키워드 매칭 / exact keyword match
        if symptom_lower in CRITICAL_SYMPTOM_KEYWORDS:
            mapped = CRITICAL_SYMPTOM_KEYWORDS[symptom_lower]
            if urgency_order[mapped] > urgency_order[max_urgency]:
                logger.warning(
                    "[Guardrail] Symptom escalation: '%s' → %s (was %s)",
                    symptom, mapped.value, max_urgency.value,
                )
                result.warnings.append(
                    f"🔺 Escalated: symptom '{symptom}' triggers {mapped.value} urgency. "
                    f"(증상 '{symptom}'으로 인해 {mapped.value}로 상향)"
                )
                max_urgency = mapped
            continue

        # 부분 매칭 — 증상 설명에 키워드가 포함된 경우
        # Partial match — symptom description contains a keyword
        for keyword, mapped in CRITICAL_SYMPTOM_KEYWORDS.items():
            if keyword in symptom_lower:
                if urgency_order[mapped] > urgency_order[max_urgency]:
                    logger.warning(
                        "[Guardrail] Symptom escalation (partial): '%s' matched '%s' → %s",
                        symptom, keyword, mapped.value,
                    )
                    result.warnings.append(
                        f"🔺 Escalated: symptom '{symptom}' (matched '{keyword}') "
                        f"triggers {mapped.value}. "
                        f"(증상 '{symptom}'에서 '{keyword}' 감지 → {mapped.value})"
                    )
                    max_urgency = mapped
                break  # 첫 매칭에서 중단 / stop at first match

    if max_urgency != current_urgency:
        result.modified_data["urgency"] = max_urgency
        result.modified_data["previous_urgency"] = current_urgency

    result.modified_data.setdefault("urgency", max_urgency)
    return result


def check_confidence_threshold(
    confidence: float,
    current_urgency: UrgencyLevel = UrgencyLevel.LOW,
    threshold: float = 0.7,
) -> GuardrailResult:
    """신뢰도가 임계값 미만이면 자동 상향한다.
    Auto-escalate if confidence score is below threshold.

    에이전트의 판단 신뢰도가 낮으면 사람의 판단이 필요하다는 의미이다.
    Low agent confidence means human judgment is needed.

    Args:
        confidence: 에이전트 판단 신뢰도 (0.0 ~ 1.0) / agent confidence score
        current_urgency: 현재 긴급도 / current urgency level
        threshold: 임계값 (기본 0.7) / threshold (default 0.7)

    Returns:
        GuardrailResult: confidence < threshold이면 한 단계 상향
                         escalate one level if confidence < threshold
    """
    result = GuardrailResult()

    if not 0.0 <= confidence <= 1.0:
        result.warnings.append(
            f"Invalid confidence value: {confidence}. Must be 0.0-1.0. "
            f"(유효하지 않은 신뢰도 값: {confidence})"
        )
        return result

    if confidence < threshold:
        urgency_order = {
            UrgencyLevel.LOW: 0,
            UrgencyLevel.MEDIUM: 1,
            UrgencyLevel.HIGH: 2,
            UrgencyLevel.EMERGENCY: 3,
        }
        reverse_order = {v: k for k, v in urgency_order.items()}

        current_level = urgency_order[current_urgency]
        # 한 단계 상향, 최대 EMERGENCY / escalate one level, cap at EMERGENCY
        new_level = min(current_level + 1, 3)
        new_urgency = reverse_order[new_level]

        result.modified_data["urgency"] = new_urgency
        result.modified_data["previous_urgency"] = current_urgency
        result.modified_data["confidence"] = confidence
        result.warnings.append(
            f"🔺 Low confidence ({confidence:.2f} < {threshold:.2f}): "
            f"escalated {current_urgency.value} → {new_urgency.value}. "
            f"(낮은 신뢰도로 인해 자동 상향: {current_urgency.value} → {new_urgency.value})"
        )
        logger.warning(
            "[Guardrail] Low confidence escalation: %.2f < %.2f, %s → %s",
            confidence, threshold, current_urgency.value, new_urgency.value,
        )
    else:
        result.modified_data["urgency"] = current_urgency
        result.modified_data["confidence"] = confidence

    return result


# =============================================================================
# 통합 가드레일 실행기 / Unified Guardrail Runner
# =============================================================================

def run_all_guardrails(
    *,
    drug_name: str | None = None,
    proposed_dosage: float | None = None,
    patient_allergies: list[str] | None = None,
    recommended_foods: list[str] | None = None,
    reported_symptoms: list[str] | None = None,
    confidence: float | None = None,
    current_urgency: UrgencyLevel = UrgencyLevel.LOW,
) -> GuardrailResult:
    """모든 관련 가드레일을 한 번에 실행한다.
    Run all applicable guardrails in a single call.

    각 가드레일의 결과를 합산하여 최종 결과를 반환한다.
    Aggregates results from all applicable guardrails.

    사용 예 / Usage example:
        result = run_all_guardrails(
            drug_name="metformin",
            proposed_dosage=3000,
            patient_allergies=["peanut"],
            recommended_foods=["peanut salad"],
            reported_symptoms=["chest pain", "mild headache"],
            confidence=0.5,
        )
        if not result.passed:
            # 위반사항 처리 / handle violations
            ...
    """
    combined = GuardrailResult()
    final_urgency = current_urgency

    # ── 1. 약물 용량 검증 / Drug dosage validation ──
    if drug_name and proposed_dosage is not None:
        dosage_result = validate_dosage(drug_name, proposed_dosage)
        combined.violations.extend(dosage_result.violations)
        combined.warnings.extend(dosage_result.warnings)
        if not dosage_result.passed:
            combined.passed = False

    # ── 2. 알레르기 식품 차단 / Allergy food conflict check ──
    if patient_allergies and recommended_foods:
        allergy_result = check_allergy_food_conflict(patient_allergies, recommended_foods)
        combined.violations.extend(allergy_result.violations)
        combined.warnings.extend(allergy_result.warnings)
        if not allergy_result.passed:
            combined.passed = False

    # ── 3. 위험 증상 자동 상향 / Critical symptom auto-escalation ──
    if reported_symptoms:
        symptom_result = escalate_by_symptoms(reported_symptoms, final_urgency)
        combined.warnings.extend(symptom_result.warnings)
        final_urgency = symptom_result.modified_data.get("urgency", final_urgency)

    # ── 4. 신뢰도 기반 자동 상향 / Confidence-based auto-escalation ──
    if confidence is not None:
        confidence_result = check_confidence_threshold(confidence, final_urgency)
        combined.warnings.extend(confidence_result.warnings)
        final_urgency = confidence_result.modified_data.get("urgency", final_urgency)

    combined.modified_data["urgency"] = final_urgency
    return combined
