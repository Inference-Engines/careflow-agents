"""
Task Agent Tool Tests / 태스크 에이전트 도구 테스트
====================================================
Mock DB 기반으로 동작. Gemini API 호출 없이 순수 로직만 테스트.
Runs against mock data only — no Gemini API calls.

pytest-asyncio 사용 금지 — 일반 pytest만 사용.
No pytest-asyncio — standard pytest only.

최소 10개 테스트 케이스 포함 / Contains 10+ test cases.
"""

import re
from unittest.mock import patch, MagicMock

import pytest

# conftest에서 FakeCtx 가져오기 / Import FakeCtx from conftest
from careflow.tests.conftest import FakeCtx, PATIENT_UUID


# ---------------------------------------------------------------------------
# ToolContext mock 헬퍼 / ToolContext mock helper
# ---------------------------------------------------------------------------

def _make_ctx(state: dict | None = None) -> FakeCtx:
    """기본 환자 state가 포함된 FakeCtx 생성.
    Create FakeCtx with default patient state.
    """
    s = {"current_patient_id": PATIENT_UUID}
    if state:
        s.update(state)
    return FakeCtx(state=s)


# ===========================================================================
# 1. get_current_medications / 현재 약물 조회
# ===========================================================================

class TestGetCurrentMedications:
    """get_current_medications mock 테스트."""

    @patch("careflow.agents.task.tools._resolve_patient_id", side_effect=lambda pid, ctx: "patient_001")
    @patch("careflow.agents.task.tools._is_db_available", return_value=False)
    def test_returns_mock_medications(self, _mock_db, _mock_resolve):
        """AlloyDB 미사용 시 mock 데이터 5개 약물 반환."""
        from careflow.agents.task.tools import get_current_medications

        ctx = _make_ctx()
        result = get_current_medications("patient_001", ctx)

        assert result["status"] == "success"
        assert result["source"] == "mock"
        assert result["medication_count"] == 5
        assert len(result["medications"]) == 5
        names = {m["name"] for m in result["medications"]}
        assert "Metformin" in names
        assert "Lisinopril" in names

    @patch("careflow.agents.task.tools._is_db_available", return_value=False)
    def test_patient_id_resolved(self, _mock_db):
        """placeholder 'patient_001'가 UUID로 교정되어야 함.
        Placeholder should be resolved to UUID.
        """
        from careflow.agents.task.tools import get_current_medications

        ctx = _make_ctx()
        result = get_current_medications("patient_001", ctx)
        assert result["patient_id"] == PATIENT_UUID


# ===========================================================================
# 2. add_medication / 약물 추가
# ===========================================================================

class TestAddMedication:
    """add_medication mock 테스트."""

    @patch("careflow.agents.task.tools._resolve_patient_id", side_effect=lambda pid, ctx: "patient_001")
    @patch("careflow.agents.task.tools._is_db_available", return_value=False)
    def test_adds_medication_to_state(self, _mock_db, _mock_resolve):
        """새 약물 추가 후 state에 반영되는지 확인."""
        from careflow.agents.task.tools import add_medication, get_current_medications

        ctx = _make_ctx()
        result = add_medication(
            patient_id="patient_001",
            name="Glimepiride",
            dosage="2mg",
            frequency="once_daily",
            timing="before_breakfast",
            tool_context=ctx,
        )
        assert result["status"] == "success"
        assert result["name"] == "Glimepiride"
        assert result["medication_id"].startswith("MED-")

        # 추가 후 총 6개 약물이어야 함 / Should now have 6 medications
        meds_result = get_current_medications("patient_001", ctx)
        assert meds_result["medication_count"] == 6


# ===========================================================================
# 3. check_drug_interactions (openFDA hit) / 약물 상호작용 (openFDA 경로)
# ===========================================================================

class TestCheckDrugInteractionsOpenFDA:
    """openFDA 레이어에서 상호작용 감지 테스트."""

    @patch("careflow.agents.task.tools.query_dict", return_value=[])
    def test_openfda_hit(self, _mock_query):
        """openFDA에서 상호작용 발견 시 결과 반환."""
        from careflow.agents.task.tools import check_drug_interactions

        mock_fda_result = {
            "status": "checked",
            "interaction_count": 1,
            "interactions": [
                {
                    "drug_pair": ["Warfarin", "Aspirin"],
                    "severity": "HIGH",
                    "description": "Increased bleeding risk",
                    "source": "openfda_drug_label",
                },
            ],
        }

        with patch(
            "careflow.agents.shared.openfda_api.check_drug_interactions_via_fda",
            return_value=mock_fda_result,
        ):
            ctx = _make_ctx()
            result = check_drug_interactions("Warfarin", ["Aspirin"], ctx)

        assert result["status"] == "interactions_detected"
        assert result["source"] == "openfda_drug_label"
        assert result["interaction_count"] == 1
        assert result["safety_check"] == "warning"


# ===========================================================================
# 4. check_drug_interactions (local fallback) / 약물 상호작용 (로컬 폴백)
# ===========================================================================

class TestCheckDrugInteractionsLocalFallback:
    """openFDA 실패 → 로컬 하드코딩 폴백 테스트."""

    @patch("careflow.agents.task.tools.query_dict", return_value=[])
    def test_local_fallback_warfarin_aspirin(self, _mock_query):
        """openFDA 실패 시 로컬 테이블에서 warfarin-aspirin 상호작용 탐지."""
        from careflow.agents.task.tools import check_drug_interactions

        # openFDA 호출 실패 시뮬레이션 / Simulate openFDA failure
        with patch(
            "careflow.agents.shared.openfda_api.check_drug_interactions_via_fda",
            side_effect=Exception("Network error"),
        ):
            ctx = _make_ctx()
            result = check_drug_interactions("Warfarin", ["Aspirin"], ctx)

        assert result["status"] == "interactions_detected"
        assert result["source"] == "local_fallback"
        assert result["interaction_count"] > 0

    @patch("careflow.agents.task.tools.query_dict", return_value=[])
    def test_local_fallback_no_interaction(self, _mock_query):
        """로컬 테이블에도 없는 약물 조합 → no_interactions."""
        from careflow.agents.task.tools import check_drug_interactions

        with patch(
            "careflow.agents.shared.openfda_api.check_drug_interactions_via_fda",
            side_effect=Exception("Network error"),
        ):
            ctx = _make_ctx()
            result = check_drug_interactions("Vitamin_D", ["Calcium"], ctx)

        assert result["status"] == "no_interactions"


# ===========================================================================
# 5. resolve_patient_id / 환자 ID 교정
# ===========================================================================

class TestResolvePatientId:
    """resolve_patient_id 테스트 — UUID vs placeholder."""

    def test_valid_uuid_passthrough(self):
        """정상 UUID는 그대로 통과. Valid UUID passes through."""
        from careflow.agents.shared.patient_utils import resolve_patient_id

        ctx = _make_ctx()
        result = resolve_patient_id(PATIENT_UUID, ctx)
        assert result == PATIENT_UUID

    def test_placeholder_resolved_to_state(self):
        """placeholder → state의 UUID로 교정."""
        from careflow.agents.shared.patient_utils import resolve_patient_id

        ctx = _make_ctx()
        result = resolve_patient_id("patient_001", ctx)
        assert result == PATIENT_UUID

    def test_no_state_uses_default(self):
        """state에도 없으면 기본값 사용. Falls back to default UUID."""
        from careflow.agents.shared.patient_utils import resolve_patient_id

        result = resolve_patient_id("patient_001", None)
        assert result == PATIENT_UUID


# ===========================================================================
# 6. Severity Classification / 심각도 분류
# ===========================================================================

class TestSeverityClassification:
    """_classify_interaction_severity, _max_severity 테스트."""

    def test_classify_warning(self):
        """HIGH severity → warning."""
        from careflow.agents.task.tools import _classify_interaction_severity

        normalized = [{"severity": "HIGH", "medication1": "A", "medication2": "B"}]
        assert _classify_interaction_severity(normalized) == "warning"

    def test_classify_info(self):
        """LOW severity → info."""
        from careflow.agents.task.tools import _classify_interaction_severity

        normalized = [{"severity": "LOW", "medication1": "A", "medication2": "B"}]
        assert _classify_interaction_severity(normalized) == "info"

    def test_max_severity(self):
        """가장 높은 severity 반환."""
        from careflow.agents.task.tools import _max_severity

        assert _max_severity(["LOW", "HIGH", "MODERATE"]) == "HIGH"
        assert _max_severity(["LOW"]) == "LOW"
        assert _max_severity([]) == "INFO"


# ===========================================================================
# 7. HITL Trigger / HITL 트리거
# ===========================================================================

class TestHITLTrigger:
    """_trigger_hitl_if_needed 테스트."""

    def test_trigger_sets_pending_hitl(self):
        """warning 상호작용 시 pending_hitl state 설정."""
        from careflow.agents.task.tools import _trigger_hitl_if_needed

        ctx = _make_ctx()
        normalized = [
            {"severity": "HIGH", "medication1": "Warfarin", "medication2": "Aspirin"}
        ]
        _trigger_hitl_if_needed(ctx, "warning", normalized, "local_fallback")

        assert "pending_hitl" in ctx.state
        assert ctx.state["pending_hitl"]["action_type"] == "drug_interaction_warning"
        assert ctx.state["pending_hitl"]["severity"] == "HIGH"

    def test_no_trigger_on_info(self):
        """info 수준에서는 pending_hitl 미설정."""
        from careflow.agents.task.tools import _trigger_hitl_if_needed

        ctx = _make_ctx()
        _trigger_hitl_if_needed(ctx, "info", [], "local_fallback")
        assert "pending_hitl" not in ctx.state

    def test_no_trigger_without_context(self):
        """tool_context=None 에서도 에러 없이 동작."""
        from careflow.agents.task.tools import _trigger_hitl_if_needed

        # Should not raise / 에러 없어야 함
        _trigger_hitl_if_needed(None, "warning", [], "local_fallback")
