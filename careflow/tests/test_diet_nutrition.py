"""
Diet/Nutrition Agent — Unit Tests
식이/영양 에이전트 — 유닛 테스트

Gemini API 없이 mock 기반으로 동작하는 테스트.
Mock-based tests that run without the real Gemini API.
"""

from unittest.mock import MagicMock, patch

import pytest

from careflow.agents.diet_nutrition.tools import (
    check_food_drug_interaction,
    get_patient_medications,
    lookup_food_nutrition,
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


# Auto-mock _resolve_patient_id and query_dict for all tests in this module
@pytest.fixture(autouse=True)
def _mock_resolve_and_db():
    with patch("careflow.agents.diet_nutrition.tools._resolve_patient_id", side_effect=lambda pid, ctx: pid), \
         patch("careflow.agents.diet_nutrition.tools.query_dict", return_value=[]):
        yield


# ---------------------------------------------------------------------------
# get_patient_medications 테스트 / Tests for get_patient_medications
# ---------------------------------------------------------------------------

class TestGetPatientMedications:
    """get_patient_medications 함수 테스트 / Tests for get_patient_medications function."""

    def test_get_patient_medications(self, mock_tool_context: MagicMock):
        """patient_001 (Rajesh)의 약물 목록이 반환되는지 확인.
        Verify medication list is returned for patient_001 (Rajesh).

        NOTE: mock 데이터 기준 patient_001은 2개 약물을 복용 중.
        Based on mock data, patient_001 has 2 medications.
        """
        result = get_patient_medications(
            patient_id="patient_001",
            tool_context=mock_tool_context,
        )

        assert "error" not in result
        assert result["patient_id"] == "patient_001"
        assert result["count"] == 2
        assert len(result["medications"]) == 2

        # 약물 이름 확인 / Verify drug names
        drug_names = [m["drug_name"] for m in result["medications"]]
        assert "Metformin" in drug_names
        assert "Amlodipine" in drug_names


# ---------------------------------------------------------------------------
# lookup_food_nutrition 테스트 / Tests for lookup_food_nutrition
# ---------------------------------------------------------------------------

class TestLookupFoodNutrition:
    """lookup_food_nutrition 함수 테스트 / Tests for lookup_food_nutrition function."""

    def test_lookup_food_nutrition_known(self, mock_tool_context: MagicMock):
        """알려진 음식(white rice)의 영양 정보가 반환되는지 확인.
        Verify nutrition data is returned for a known food item (white rice).
        """
        result = lookup_food_nutrition(
            food_name="white rice",
            tool_context=mock_tool_context,
        )

        assert result["found"] is True
        assert "calories_kcal" in result
        assert result["calories_kcal"] == 206
        assert "sodium_mg" in result
        assert "glycemic_index" in result

    def test_lookup_food_nutrition_unknown(self, mock_tool_context: MagicMock):
        """등록되지 않은 음식에 대해 — mock에 없으면 API fallback 시도.
        Unknown food — not in mock DB, may fallback to USDA API.
        If API finds it, found=True (real API working). If not, found=False.
        """
        result = lookup_food_nutrition(
            food_name="xyznonexistentfood12345",
            tool_context=mock_tool_context,
        )

        assert result["found"] is False


# ---------------------------------------------------------------------------
# check_food_drug_interaction 테스트 / Tests for check_food_drug_interaction
# ---------------------------------------------------------------------------

class TestCheckFoodDrugInteraction:
    """check_food_drug_interaction 함수 테스트 / Tests for check_food_drug_interaction function."""

    def test_check_food_drug_interaction_found(self, mock_tool_context: MagicMock):
        """grapefruit + Amlodipine 상호작용이 올바르게 감지되는지 확인.
        Verify grapefruit + Amlodipine interaction is correctly detected.
        """
        result = check_food_drug_interaction(
            food_name="grapefruit",
            drug_name="Amlodipine",
            tool_context=mock_tool_context,
        )

        assert result["interaction_found"] is True
        assert result["severity"] == "WARNING"
        assert "CYP3A4" in result["interaction"]
        assert result["food"] == "grapefruit"
        assert result["drug"] == "Amlodipine"

    def test_check_food_drug_interaction_safe(self, mock_tool_context: MagicMock):
        """안전한 음식-약물 조합에서 상호작용이 없는지 확인.
        Verify no interaction for a safe food-drug combination.
        """
        result = check_food_drug_interaction(
            food_name="brown rice",
            drug_name="Metformin",
            tool_context=mock_tool_context,
        )

        assert result["interaction_found"] is False
        assert "No known interaction" in result["message"]
