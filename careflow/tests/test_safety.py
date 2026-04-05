"""
Safety Guardrails — Unit Tests
안전 가드레일 — 유닛 테스트

결정론적 가드레일 규칙의 정확성을 검증하는 테스트.
Tests verifying correctness of deterministic guardrail rules.
Gemini API 호출 없이 순수 로직만 테스트한다.
Tests pure logic without any Gemini API calls.
"""

import pytest

from careflow.agents.safety.guardrails import (
    GuardrailResult,
    UrgencyLevel,
    check_allergy_food_conflict,
    check_confidence_threshold,
    escalate_by_symptoms,
    validate_dosage,
)


# ---------------------------------------------------------------------------
# validate_dosage 테스트 / Tests for validate_dosage
# ---------------------------------------------------------------------------

class TestValidateDosage:
    """validate_dosage 함수 테스트 / Tests for validate_dosage function."""

    def test_guardrail_dosage_valid(self):
        """Metformin 1000mg/day가 정상 범위 내인지 확인.
        Verify Metformin 1000mg/day is within safe range (500-2550).
        """
        result = validate_dosage(drug_name="Metformin", proposed_mg_per_day=1000)

        assert result.passed is True
        assert len(result.violations) == 0

    def test_guardrail_dosage_exceeded(self):
        """Metformin 5000mg/day가 최대 용량 초과로 차단되는지 확인.
        Verify Metformin 5000mg/day is blocked for exceeding max safe dose (2550).
        """
        result = validate_dosage(drug_name="Metformin", proposed_mg_per_day=5000)

        assert result.passed is False
        assert len(result.violations) > 0
        assert "BLOCKED" in result.violations[0]
        assert "maximum safe dose" in result.violations[0].lower() or "exceeds" in result.violations[0].lower()


# ---------------------------------------------------------------------------
# check_allergy_food_conflict 테스트 / Tests for check_allergy_food_conflict
# ---------------------------------------------------------------------------

class TestCheckAllergyFoodConflict:
    """check_allergy_food_conflict 함수 테스트 / Tests for check_allergy_food_conflict function."""

    def test_guardrail_allergy_conflict(self):
        """peanut 알레르기 환자에게 peanut butter가 차단되는지 확인.
        Verify peanut butter is blocked for a patient with peanut allergy.
        """
        result = check_allergy_food_conflict(
            patient_allergies=["peanut"],
            recommended_foods=["peanut butter sandwich", "apple"],
        )

        assert result.passed is False
        assert len(result.violations) > 0
        # 위반 메시지에 알레르기 관련 정보가 포함되어야 함
        # Violation message should contain allergy-related info
        violation_text = " ".join(result.violations)
        assert "peanut" in violation_text.lower()
        assert "BLOCKED" in violation_text


# ---------------------------------------------------------------------------
# escalate_by_symptoms 테스트 / Tests for escalate_by_symptoms
# ---------------------------------------------------------------------------

class TestEscalateBySymptoms:
    """escalate_by_symptoms 함수 테스트 / Tests for escalate_by_symptoms function."""

    def test_guardrail_symptom_escalation_high(self):
        """chest_pain 증상이 EMERGENCY로 자동 상향되는지 확인.
        Verify chest_pain auto-escalates to EMERGENCY level.
        """
        result = escalate_by_symptoms(
            reported_symptoms=["chest_pain"],
            current_urgency=UrgencyLevel.LOW,
        )

        final_urgency = result.modified_data.get("urgency")
        assert final_urgency == UrgencyLevel.EMERGENCY
        assert len(result.warnings) > 0
        # 이전 긴급도가 기록되어야 함 / Previous urgency should be recorded
        assert result.modified_data.get("previous_urgency") == UrgencyLevel.LOW


# ---------------------------------------------------------------------------
# check_confidence_threshold 테스트 / Tests for check_confidence_threshold
# ---------------------------------------------------------------------------

class TestCheckConfidenceThreshold:
    """check_confidence_threshold 함수 테스트 / Tests for check_confidence_threshold function."""

    def test_guardrail_confidence_upgrade(self):
        """confidence 0.5가 임계값(0.7) 미만일 때 긴급도가 한 단계 상향되는지 확인.
        Verify urgency is escalated one level when confidence (0.5) < threshold (0.7).
        """
        result = check_confidence_threshold(
            confidence=0.5,
            current_urgency=UrgencyLevel.LOW,
            threshold=0.7,
        )

        final_urgency = result.modified_data.get("urgency")
        # LOW → MEDIUM으로 한 단계 상향 / Escalated one level: LOW → MEDIUM
        assert final_urgency == UrgencyLevel.MEDIUM
        assert result.modified_data.get("previous_urgency") == UrgencyLevel.LOW
        assert len(result.warnings) > 0
        assert "Low confidence" in result.warnings[0] or "낮은 신뢰도" in result.warnings[0]
