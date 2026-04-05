"""
Output Schemas — Unit Tests
출력 스키마 — 유닛 테스트

Pydantic 모델의 유효성 검증 로직을 테스트한다.
Tests Pydantic model validation logic.
Gemini API 호출 없이 스키마 검증만 수행한다.
Only schema validation — no Gemini API calls.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from careflow.schemas.output_schemas import (
    DateRange,
    EscalationAction,
    HealthInsightOutput,
    SymptomTriageOutput,
    UrgencyLevel,
)


# ---------------------------------------------------------------------------
# HealthInsightOutput 테스트 / Tests for HealthInsightOutput
# ---------------------------------------------------------------------------

class TestHealthInsightOutput:
    """HealthInsightOutput 스키마 테스트 / Tests for HealthInsightOutput schema."""

    def test_health_insight_output_valid(self):
        """정상 데이터로 HealthInsightOutput 검증이 통과하는지 확인.
        Verify HealthInsightOutput passes validation with valid data.
        """
        output = HealthInsightOutput(
            insight_type="trend_alert",
            severity="warning",
            title="Systolic blood pressure rising over 3 months",
            content="Systolic BP increased 10 mmHg over 90 days (130 -> 140).",
            confidence=0.88,
            recommendations=["Discuss blood pressure medication adjustment at next visit."],
            data_range=DateRange(start=date(2026, 1, 3), end=date(2026, 4, 3)),
            icd11_codes=["BA00"],
        )

        assert output.insight_type == "trend_alert"
        assert output.severity == "warning"
        assert output.confidence == 0.88
        assert len(output.recommendations) == 1
        assert output.data_range.start == date(2026, 1, 3)


# ---------------------------------------------------------------------------
# SymptomTriageOutput 테스트 / Tests for SymptomTriageOutput
# ---------------------------------------------------------------------------

class TestSymptomTriageOutput:
    """SymptomTriageOutput 스키마 테스트 / Tests for SymptomTriageOutput schema."""

    def test_symptom_triage_output_requires_symptoms(self):
        """빈 증상 리스트가 Pydantic 검증에서 거부되는지 확인.
        Verify empty symptom list is rejected by Pydantic validation (min_length=1).
        """
        with pytest.raises(ValidationError) as exc_info:
            SymptomTriageOutput(
                reported_symptoms=[],  # 빈 리스트 — 거부되어야 함 / empty — should be rejected
                urgency_level="MEDIUM",
                confidence=0.8,
                analysis="Test analysis",
                recommendation="Test recommendation",
                escalation=EscalationAction(
                    notify_caregiver=True,
                    notify_doctor=False,
                    recommend_er=False,
                ),
                safe_default_applied=False,
            )

        # min_length 위반 에러가 포함되어야 함
        # Validation error should mention the min_length constraint
        error_str = str(exc_info.value)
        assert "reported_symptoms" in error_str or "too_short" in error_str


# ---------------------------------------------------------------------------
# UrgencyLevel Enum 테스트 / Tests for UrgencyLevel Enum
# ---------------------------------------------------------------------------

class TestUrgencyLevelEnum:
    """UrgencyLevel 열거형 테스트 / Tests for UrgencyLevel enum."""

    def test_urgency_level_enum(self):
        """LOW, MEDIUM, HIGH만 유효한 값인지 확인.
        Verify only LOW, MEDIUM, HIGH are valid UrgencyLevel values.
        """
        # 유효한 값 확인 / Valid values
        assert UrgencyLevel.LOW == "LOW"
        assert UrgencyLevel.MEDIUM == "MEDIUM"
        assert UrgencyLevel.HIGH == "HIGH"

        # 유효한 값 목록 확인 / Verify valid value list
        valid_values = [level.value for level in UrgencyLevel]
        assert "LOW" in valid_values
        assert "MEDIUM" in valid_values
        assert "HIGH" in valid_values

        # 잘못된 값으로 생성 시도 → ValueError 발생
        # Attempting to create with invalid value → raises ValueError
        with pytest.raises(ValueError):
            UrgencyLevel("CRITICAL")

        with pytest.raises(ValueError):
            UrgencyLevel("INVALID")
