"""
Symptom Triage Agent — Unit Tests
증상 분류 에이전트 — 유닛 테스트

Gemini API 없이 mock 기반으로 동작하는 테스트.
Mock-based tests that run without the real Gemini API.
"""

from unittest.mock import MagicMock, patch

import pytest

from careflow.agents.symptom_triage.tools import (
    lookup_icd11_code,
    send_escalation_alert,
)


# ---------------------------------------------------------------------------
# Fixture: ToolContext mock 생성 / Create a mock ToolContext
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tool_context() -> MagicMock:
    """ToolContext를 mock 객체로 대체한다 / Replace ToolContext with a mock."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


# ---------------------------------------------------------------------------
# ICD-11 매핑 mock 데이터 / Mock data for ICD-11 mapping
# 파일 I/O 없이 테스트하기 위해 _load_icd11_mapping을 mock한다.
# Mock _load_icd11_mapping to avoid file I/O during tests.
# ---------------------------------------------------------------------------

_MOCK_ICD11_MAPPING = {
    "dizziness": {"code": "MB48.0", "title": "Dizziness"},
    "chest_pain": {"code": "MD30", "title": "Chest pain"},
    "headache": {"code": "MG31", "title": "Headache"},
    "nausea": {"code": "MD90", "title": "Nausea"},
    "tremor": {"code": "MB48.1", "title": "Tremor"},
}


# ---------------------------------------------------------------------------
# lookup_icd11_code 테스트 / Tests for lookup_icd11_code
# ---------------------------------------------------------------------------

class TestLookupIcd11Code:
    """lookup_icd11_code 함수 테스트 / Tests for lookup_icd11_code function."""

    @patch(
        "careflow.agents.symptom_triage.tools._load_icd11_mapping",
        return_value=_MOCK_ICD11_MAPPING,
    )
    def test_lookup_icd11_code_known(self, mock_load, mock_tool_context: MagicMock):
        """dizziness가 MB48.0으로 올바르게 매핑되는지 확인.
        Verify dizziness maps to MB48.0 correctly.
        """
        result = lookup_icd11_code(symptom="dizziness", tool_context=mock_tool_context)

        assert result["status"] == "success"
        assert result["icd11_code"] == "MB48.0"
        assert result["icd11_title"] == "Dizziness"

    @patch(
        "careflow.agents.symptom_triage.tools._load_icd11_mapping",
        return_value=_MOCK_ICD11_MAPPING,
    )
    def test_lookup_icd11_code_unknown(self, mock_load, mock_tool_context: MagicMock):
        """등록되지 않은 증상에 대해 not_found 상태를 반환하는지 확인.
        Verify not_found status for an unknown symptom.
        """
        result = lookup_icd11_code(
            symptom="alien_abduction_syndrome",
            tool_context=mock_tool_context,
        )

        assert result["status"] == "not_found"
        assert "No ICD-11 mapping found" in result["message"]


# ---------------------------------------------------------------------------
# send_escalation_alert 테스트 / Tests for send_escalation_alert
# ---------------------------------------------------------------------------

class TestSendEscalationAlert:
    """send_escalation_alert 함수 테스트 / Tests for send_escalation_alert function."""

    def test_send_escalation_high_forces_doctor(self, mock_tool_context: MagicMock):
        """HIGH 긴급도에서 notify_doctor=False여도 True로 강제 상향되는지 확인.
        Verify HIGH urgency forces notify_doctor=True even when passed as False.
        """
        result = send_escalation_alert(
            patient_id="patient_001",
            urgency="HIGH",
            message="Severe dizziness and chest tightness",
            notify_caregiver=False,  # 강제로 True가 되어야 함 / should be forced to True
            notify_doctor=False,     # 강제로 True가 되어야 함 / should be forced to True
            tool_context=mock_tool_context,
        )

        assert result["status"] == "success"
        assert result["urgency"] == "HIGH"
        # HIGH 긴급도에서 의사와 보호자 모두 알림이 전송되어야 함
        # Both doctor and caregiver must be notified for HIGH urgency
        assert "doctor" in str(result["notifications_sent_to"])
        assert "caregiver" in str(result["notifications_sent_to"])
        assert len(result["notifications_sent_to"]) == 2

    def test_send_escalation_medium_forces_caregiver(self, mock_tool_context: MagicMock):
        """MEDIUM 긴급도에서 notify_caregiver=False여도 True로 강제되는지 확인.
        Verify MEDIUM urgency forces notify_caregiver=True even when passed as False.
        """
        result = send_escalation_alert(
            patient_id="patient_001",
            urgency="MEDIUM",
            message="Mild dizziness reported",
            notify_caregiver=False,  # 강제로 True가 되어야 함 / should be forced to True
            notify_doctor=False,
            tool_context=mock_tool_context,
        )

        assert result["status"] == "success"
        assert result["urgency"] == "MEDIUM"
        # MEDIUM 긴급도에서 보호자 알림이 강제되어야 함
        # Caregiver notification must be forced for MEDIUM urgency
        assert "caregiver" in str(result["notifications_sent_to"])
        assert len(result["notifications_sent_to"]) == 1  # 보호자만 / caregiver only

        # 에스컬레이션 로그가 state에 저장되는지 확인
        # Verify escalation log is persisted in state
        assert "escalation_log" in mock_tool_context.state
        assert len(mock_tool_context.state["escalation_log"]) == 1
