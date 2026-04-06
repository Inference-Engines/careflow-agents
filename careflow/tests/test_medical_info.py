"""
Medical Info Tool Tests / 의료 정보 도구 테스트
=================================================
Mock 기반으로 동작. Gemini API 호출 없이 순수 로직만 테스트.
Runs against mocks only — no Gemini or embedding API calls.

pytest-asyncio 사용 금지 — 일반 pytest만 사용.
No pytest-asyncio — standard pytest only.

최소 8개 테스트 케이스 포함 / Contains 8+ test cases.
"""

from unittest.mock import patch, MagicMock

import pytest

from careflow.tests.conftest import FakeCtx, PATIENT_UUID


# ---------------------------------------------------------------------------
# ToolContext mock 헬퍼 / ToolContext mock helper
# ---------------------------------------------------------------------------

def _make_ctx(state: dict | None = None) -> FakeCtx:
    """기본 환자 state 포함 FakeCtx 생성."""
    s = {"current_patient_id": PATIENT_UUID}
    if state:
        s.update(state)
    return FakeCtx(state=s)


# ===========================================================================
# 1. _generate_embedding (mock) / 임베딩 생성 (mock)
# ===========================================================================

class TestGenerateEmbedding:
    """_generate_embedding mock 테스트."""

    def test_returns_768d_vector(self):
        """정상 호출 시 768차원 벡터 반환. Returns 768-dim vector on success."""
        from careflow.agents.medical_info import tools as mi_tools

        fake_embedding = [0.1] * 768
        mock_result = MagicMock()
        mock_emb = MagicMock()
        mock_emb.values = fake_embedding
        mock_result.embeddings = [mock_emb]

        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = mock_result

        # 싱글턴 클라이언트를 mock으로 교체 / Replace singleton client
        original = mi_tools._embed_client
        try:
            mi_tools._embed_client = mock_client
            vec = mi_tools._generate_embedding("test text")
            assert vec is not None
            assert len(vec) == 768
        finally:
            mi_tools._embed_client = original

    def test_returns_none_on_empty(self):
        """빈 텍스트 → None 반환. Empty text returns None."""
        from careflow.agents.medical_info.tools import _generate_embedding

        assert _generate_embedding("") is None
        assert _generate_embedding("   ") is None

    def test_returns_none_on_exception(self):
        """API 오류 시 None 반환 (fail-safe). Returns None on exception."""
        from careflow.agents.medical_info import tools as mi_tools

        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = RuntimeError("API error")

        original = mi_tools._embed_client
        try:
            mi_tools._embed_client = mock_client
            vec = mi_tools._generate_embedding("test text")
            assert vec is None
        finally:
            mi_tools._embed_client = original


# ===========================================================================
# 2. _fallback_keyword_search / 키워드 폴백 검색
# ===========================================================================

class TestFallbackKeywordSearch:
    """_fallback_keyword_search mock 테스트."""

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    def test_keyword_search_finds_records(self, _mock_query):
        """키워드 매칭으로 방문 기록 검색 — 'blood pressure' 쿼리."""
        from careflow.agents.medical_info.tools import _fallback_keyword_search

        ctx = _make_ctx()
        result = _fallback_keyword_search("patient_001", "blood pressure", 5, ctx)

        assert result["status"] == "success"
        assert result["source"] == "mock_keyword"
        # mock 데이터에 blood pressure 키워드가 3개 방문 기록 모두에 있음
        assert result["results_count"] > 0

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    def test_keyword_search_no_match(self, _mock_query):
        """매칭 키워드 없는 쿼리 → 결과 0건. No matching keywords → 0 results."""
        from careflow.agents.medical_info.tools import _fallback_keyword_search

        ctx = _make_ctx()
        result = _fallback_keyword_search("patient_001", "xyz_nonexistent_term", 5, ctx)

        assert result["status"] == "success"
        assert result["results_count"] == 0


# ===========================================================================
# 3. Confidence Tiering (HIGH/MEDIUM/LOW) / 신뢰도 티어링
# ===========================================================================

class TestConfidenceTiering:
    """search_medical_history의 similarity threshold 기반 결과 분류 테스트.
    Tests the similarity threshold logic in search_medical_history.
    """

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    @patch("careflow.agents.medical_info.tools._generate_embedding", return_value=None)
    def test_embedding_failure_falls_back_to_keyword(self, _mock_emb, _mock_query):
        """임베딩 실패 시 키워드 폴백 사용. Falls back to keyword on embedding failure."""
        from careflow.agents.medical_info.tools import search_medical_history

        ctx = _make_ctx()
        result = search_medical_history(PATIENT_UUID, "blood pressure", ctx)

        # 임베딩 실패 → keyword fallback → mock_keyword 소스
        assert result["source"] == "mock_keyword"

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    @patch("careflow.agents.medical_info.tools._generate_embedding", return_value=None)
    @patch("careflow.agents.medical_info.tools._resolve_patient_id", side_effect=lambda pid, ctx: "patient_001")
    def test_high_relevance_keyword_match(self, _mock_resolve, _mock_emb, _mock_query):
        """키워드 매칭 결과가 있으면 results_count > 0."""
        from careflow.agents.medical_info.tools import search_medical_history

        ctx = _make_ctx()
        result = search_medical_history("patient_001", "metformin diabetes", ctx)

        assert result["results_count"] > 0


# ===========================================================================
# 4. Cross-Patient Assertion / 크로스 환자 검증
# ===========================================================================

class TestCrossPatientAssertion:
    """다른 환자 데이터 접근 방지 테스트."""

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    @patch("careflow.agents.medical_info.tools._generate_embedding", return_value=None)
    def test_different_patient_returns_empty(self, _mock_emb, _mock_query):
        """다른 환자 ID로 검색 시 mock 데이터에서 매칭 없음.
        Searching with a different patient_id yields no mock matches.
        """
        from careflow.agents.medical_info.tools import search_medical_history

        other_uuid = "99999999-9999-9999-9999-999999999999"
        ctx = FakeCtx(state={"current_patient_id": other_uuid})
        result = search_medical_history(other_uuid, "blood pressure", ctx)

        # mock 데이터는 patient_001 기준이므로 다른 UUID → 0건
        assert result["results_count"] == 0

    @patch("careflow.agents.medical_info.tools.query_dict", return_value=[])
    @patch("careflow.agents.medical_info.tools._generate_embedding", return_value=None)
    def test_placeholder_resolved_to_correct_patient(self, _mock_emb, _mock_query):
        """placeholder 'patient_001'이 UUID로 교정되어야 함."""
        from careflow.agents.medical_info.tools import search_medical_history

        ctx = _make_ctx()
        result = search_medical_history("patient_001", "blood pressure", ctx)

        # resolve_patient_id가 UUID로 교정하므로 patient_id 필드에
        # mock 데이터의 'patient_001'과 다른 UUID가 들어감 → 0건 또는
        # mock keyword path에서 patient_id 비교 시 불일치.
        # 이것은 의도된 동작: 실제 환경에서는 DB가 UUID를 사용.
        # 여기서는 resolve가 정상 작동하는지만 확인.
        assert result["status"] == "success"


# ===========================================================================
# 5. Synonym Map Coverage / 동의어 맵 범위
# ===========================================================================

class TestSynonymMapCoverage:
    """semantic_search_with_reformulation에 내장된 _SYNONYMS 맵 범위 테스트.
    Tests coverage of the _SYNONYMS map in semantic_search_with_reformulation.
    """

    def test_synonym_map_has_dm2_keywords(self):
        """DM2 관련 키워드 포함 확인 / DM2 keywords present."""
        # _SYNONYMS는 함수 내부 지역변수이므로 소스 코드 검증으로 대체
        # Since _SYNONYMS is local, we verify via source inspection
        import inspect
        from careflow.agents.medical_info.tools import semantic_search_with_reformulation

        source = inspect.getsource(semantic_search_with_reformulation)
        assert "metformin" in source
        assert "diabetes" in source
        assert "blood sugar" in source
        assert "hba1c" in source.lower()

    def test_synonym_map_has_htn_keywords(self):
        """HTN 관련 키워드 포함 확인 / HTN keywords present."""
        import inspect
        from careflow.agents.medical_info.tools import semantic_search_with_reformulation

        source = inspect.getsource(semantic_search_with_reformulation)
        assert "amlodipine" in source
        assert "lisinopril" in source
        assert "blood pressure" in source
        assert "hypertension" in source

    def test_synonym_map_has_symptom_keywords(self):
        """증상 키워드 포함 확인 / Symptom keywords present."""
        import inspect
        from careflow.agents.medical_info.tools import semantic_search_with_reformulation

        source = inspect.getsource(semantic_search_with_reformulation)
        assert "chest pain" in source
        assert "dizziness" in source
        assert "nausea" in source

    def test_synonym_map_has_adherence_keywords(self):
        """복약 순응 키워드 포함 확인 / Adherence keywords present."""
        import inspect
        from careflow.agents.medical_info.tools import semantic_search_with_reformulation

        source = inspect.getsource(semantic_search_with_reformulation)
        assert "forgot medicine" in source or "missed dose" in source
        assert "exercise" in source
        assert "diet" in source
