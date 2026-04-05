"""
Health Insight Agent — Unit Tests
건강 인사이트 에이전트 — 유닛 테스트

Gemini API 없이 mock 기반으로 동작하는 테스트.
Mock-based tests that run without the real Gemini API.
"""

from unittest.mock import MagicMock

import pytest

from careflow.agents.health_insight.tools import (
    calculate_trend,
    get_health_metrics,
    get_medication_history,
)


# ---------------------------------------------------------------------------
# Fixture: ToolContext mock 생성 / Create a mock ToolContext
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tool_context() -> MagicMock:
    """ToolContext를 mock 객체로 대체한다 / Replace ToolContext with a mock."""
    ctx = MagicMock()
    ctx.state = {}  # state는 실제 dict로 동작해야 함 / state must behave as a real dict
    return ctx


# ---------------------------------------------------------------------------
# get_health_metrics 테스트 / Tests for get_health_metrics
# ---------------------------------------------------------------------------

class TestGetHealthMetrics:
    """get_health_metrics 함수 테스트 / Tests for get_health_metrics function."""

    def test_get_health_metrics_returns_data(self, mock_tool_context: MagicMock):
        """patient_001의 혈압 데이터가 정상적으로 반환되는지 확인.
        Verify blood pressure data is returned for patient_001.
        """
        result = get_health_metrics(
            patient_id="patient_001",
            metric_type="blood_pressure_systolic",
            days=365,  # 충분히 넓은 기간 / wide enough window
            tool_context=mock_tool_context,
        )

        assert result["status"] == "success"
        assert result["patient_id"] == "patient_001"
        assert result["metric_type"] == "blood_pressure_systolic"
        assert result["data_points"] > 0
        assert len(result["values"]) > 0

        # 반환된 값 구조 확인 / Verify structure of returned values
        first_entry = result["values"][0]
        assert "date" in first_entry
        assert "value" in first_entry

    def test_get_health_metrics_unknown_patient(self, mock_tool_context: MagicMock):
        """존재하지 않는 환자 ID에 대해 에러를 반환하는지 확인.
        Verify error response for unknown patient ID.
        """
        result = get_health_metrics(
            patient_id="unknown_patient",
            metric_type="blood_pressure_systolic",
            days=90,
            tool_context=mock_tool_context,
        )

        assert result["status"] == "error"
        assert "No data found" in result["message"]


# ---------------------------------------------------------------------------
# calculate_trend 테스트 / Tests for calculate_trend
# ---------------------------------------------------------------------------

class TestCalculateTrend:
    """calculate_trend 함수 테스트 / Tests for calculate_trend function."""

    def test_calculate_trend_rising(self, mock_tool_context: MagicMock):
        """상승 트렌드가 올바르게 감지되는지 확인.
        Verify rising trend is correctly detected.
        """
        # 꾸준히 상승하는 값 / Steadily increasing values
        values = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
        result = calculate_trend(values=values, tool_context=mock_tool_context)

        assert result["status"] == "success"
        assert result["trend"] == "rising"
        assert result["slope"] > 0
        assert result["data_points"] == 6
        assert result["min"] == 100.0
        assert result["max"] == 150.0

    def test_calculate_trend_stable(self, mock_tool_context: MagicMock):
        """안정 트렌드가 올바르게 감지되는지 확인.
        Verify stable trend is correctly detected.
        """
        # 거의 변화 없는 값 / Nearly constant values
        values = [100.0, 100.1, 99.9, 100.0, 100.1, 100.0]
        result = calculate_trend(values=values, tool_context=mock_tool_context)

        assert result["status"] == "success"
        assert result["trend"] == "stable"
        assert result["data_points"] == 6

        # state에 결과가 저장되는지 확인 / Verify result is cached in state
        assert "last_trend_result" in mock_tool_context.state


# ---------------------------------------------------------------------------
# get_medication_history 테스트 / Tests for get_medication_history
# ---------------------------------------------------------------------------

class TestGetMedicationHistory:
    """get_medication_history 함수 테스트 / Tests for get_medication_history function."""

    def test_get_medication_history(self, mock_tool_context: MagicMock):
        """patient_001의 약물 이력이 정상 반환되는지 확인.
        Verify medication history is returned for patient_001.
        """
        result = get_medication_history(
            patient_id="patient_001",
            tool_context=mock_tool_context,
        )

        assert result["status"] == "success"
        assert result["patient_id"] == "patient_001"
        assert result["medication_count"] == 2
        assert len(result["medications"]) == 2

        # 약물 이름 확인 / Verify medication names
        med_names = [m["medication"] for m in result["medications"]]
        assert "Metformin" in med_names
        assert "Amlodipine" in med_names

        # state에 마지막 조회 환자가 기록되는지 확인
        # Verify last queried patient is stored in state
        assert mock_tool_context.state["last_medication_query_patient"] == "patient_001"
