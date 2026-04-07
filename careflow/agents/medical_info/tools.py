# ============================================================================
# CareFlow Medical Info Agent — Function Tools
# 의료 정보 에이전트 도구 함수 정의
# ============================================================================
# Mock 데이터 기반으로 동작하는 FunctionTool 모음.
# 실제 프로덕션에서는 AlloyDB + pgvector + MCP Toolbox로 교체 예정.
#
# Tools backed by mock data for development/demo.
# In production, these will be replaced by AlloyDB/pgvector/Toolbox integration.
# ============================================================================

from collections import OrderedDict
from datetime import datetime
from typing import Optional
import json
import logging
import time

from google.adk.tools import ToolContext
from careflow.db.alloydb_client import query_dict, execute_write
from careflow.agents.shared.patient_utils import resolve_patient_id as _resolve_patient_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Embedding client (singleton)
# Gemini text-embedding-004 호출용 싱글턴 클라이언트
# ---------------------------------------------------------------------------

# 싱글턴으로 재사용 — 매 호출마다 클라이언트를 새로 만들지 않는다.
# Reused as a singleton to avoid rebuilding the client on every call.
_embed_client = None


def _generate_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    title: str | None = None,
) -> list[float] | None:
    """Generate a 768-dim embedding via Gemini ``text-embedding-004``.

    Gemini text-embedding-004 모델로 768차원 임베딩 벡터를 생성합니다.
    실패 시 None을 반환하여 호출자가 키워드 fallback 경로를 탈 수 있게 합니다.

    Args:
        text: Raw text to embed. Truncated to 5000 chars (~1200 tokens) to stay
              within text-embedding-004's 2048-token limit.

    Returns:
        A list of 768 floats, or ``None`` if the embedding call failed for
        any reason (missing credentials, network error, quota, etc.).
    """
    global _embed_client
    if not text or not text.strip():
        return None
    try:
        if _embed_client is None:
            # Lazy import — 이 모듈은 google-genai가 없어도 import 가능해야 함
            # Lazy import so the module still imports when google-genai is absent.
            from google import genai  # type: ignore
            _embed_client = genai.Client()

        # Dr. Chandra 가이드: task_type 비대칭 필수.
        # RETRIEVAL_DOCUMENT for stored text, RETRIEVAL_QUERY for search queries.
        # Symmetric usage loses 25-30% recall on medical corpora.
        from google.genai import types as genai_types  # type: ignore
        config = genai_types.EmbedContentConfig(task_type=task_type)
        if title and task_type == "RETRIEVAL_DOCUMENT":
            # title adds +3-5% nDCG@10 on structured visit records.
            config.title = title
        result = _embed_client.models.embed_content(
            model="text-embedding-005",
            contents=text[:5000],
            config=config,
        )
        # google-genai SDK returns an object with an ``embeddings`` list,
        # each entry exposing ``.values`` (list[float]).
        embeddings = getattr(result, "embeddings", None)
        if not embeddings:
            return None
        values = getattr(embeddings[0], "values", None)
        if values is None:
            return None
        return list(values)
    except Exception as e:
        logger.warning(f"embedding.failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Generative client (singleton) — HyDE 가상문서 생성 + Self-RAG reflection
# Shared Gemini Flash client for HyDE expansion and Self-RAG reflection.
# ---------------------------------------------------------------------------
_gen_client = None


class _BoundedTTLCache(OrderedDict):
    """Bounded dict cache with TTL eviction (stdlib only, no external deps).

    최대 크기 초과 시 가장 오래된 항목부터 제거하고,
    TTL이 만료된 항목은 조회 시 자동 삭제합니다.

    Evicts oldest entries when maxsize is exceeded and transparently
    removes entries whose TTL has expired on access.
    """

    def __init__(self, maxsize: int = 200, ttl: int = 3600):
        super().__init__()
        self._maxsize = maxsize
        self._ttl = ttl
        self._timestamps: dict[str, float] = {}

    def _is_expired(self, key: str) -> bool:
        ts = self._timestamps.get(key)
        return ts is not None and (time.monotonic() - ts) > self._ttl

    def __getitem__(self, key: str):
        if self._is_expired(key):
            self._evict(key)
            raise KeyError(key)
        self.move_to_end(key)
        return super().__getitem__(key)

    def get(self, key, default=None):  # noqa: D401
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        self._timestamps[key] = time.monotonic()
        while len(self) > self._maxsize:
            oldest = next(iter(self))
            self._evict(oldest)

    def __contains__(self, key):
        if super().__contains__(key):
            if self._is_expired(key):
                self._evict(key)
                return False
            return True
        return False

    def _evict(self, key: str):
        super().pop(key, None)
        self._timestamps.pop(key, None)


_HYDE_CACHE: _BoundedTTLCache = _BoundedTTLCache(maxsize=200, ttl=3600)
_REFLECT_CACHE: _BoundedTTLCache = _BoundedTTLCache(maxsize=500, ttl=3600)


def _get_gen_client():
    """Lazy singleton for the Gemini generative client."""
    global _gen_client
    if _gen_client is None:
        try:
            from google import genai  # type: ignore
            _gen_client = genai.Client()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"gen_client.init_failed: {e}")
            _gen_client = None
    return _gen_client


def _hyde_generate_hypothetical(query: str) -> str | None:
    """HyDE: Gemini Flash에 '이 질문에 답하는 가상의 의무기록 한 단락'을 쓰게 한다.

    그런 다음 이 가상문서를 임베딩해 검색에 사용 — 짧은 구어 쿼리와
    긴 임상어 문서 사이의 어휘 갭을 메꿔 recall을 크게 끌어올린다.
    (Gao et al., 2022 — Precise Zero-Shot Dense Retrieval without Relevance Labels)

    Hypothetical Document Embedding: ask Gemini Flash to draft a plausible
    medical visit note that would answer the user's query. We then embed that
    draft instead of the raw query — bridging the vocabulary gap between
    short lay queries and long clinical records.
    Cached by exact query to avoid repeat LLM calls.
    """
    q = (query or "").strip()
    if not q:
        return None
    if q in _HYDE_CACHE:
        return _HYDE_CACHE[q]
    client = _get_gen_client()
    if client is None:
        return None
    try:
        prompt = (
            "You are a medical assistant drafting a plausible clinical visit "
            "note that would answer the following patient question. Write a "
            "concise, realistic 2-3 sentence note in clinical English, including "
            "relevant vitals, diagnosis terms, medications, or test results. "
            "Do NOT add disclaimers or meta-commentary — output only the note.\n\n"
            f"Patient question: {q}\n\nHypothetical clinical note:"
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (getattr(resp, "text", "") or "").strip()
        if text:
            _HYDE_CACHE[q] = text
            logger.info("hyde.generated chars=%d query=%r", len(text), q[:60])
            return text
    except Exception as e:  # noqa: BLE001
        logger.warning(f"hyde.failed: {e}")
    return None


def _reflect_chunk_relevance(query: str, chunk_text: str) -> str:
    """Self-RAG reflection: LLM에게 'chunk가 query에 답이 되는가?' 질문.

    Returns one of: ``"YES"``, ``"PARTIAL"``, ``"NO"``.
    캐시됨 — 동일 (query, chunk_prefix) 조합 재호출 방지.

    Returns ``"YES"`` on any LLM failure (fail-open) so that embedding / network
    hiccups don't accidentally discard valid retrieved rows. Precision loss is
    acceptable; recall loss on medical records is not.
    """
    if not chunk_text:
        return "NO"
    key = f"{(query or '')[:100]}|{chunk_text[:200]}"
    cached = _REFLECT_CACHE.get(key)
    if cached is not None:
        return cached
    client = _get_gen_client()
    if client is None:
        return "YES"  # fail-open
    try:
        prompt = (
            "Does the following medical visit record ANSWER the patient's question?\n"
            "Reply with EXACTLY ONE word: YES, PARTIAL, or NO.\n\n"
            f"Question: {query}\n"
            f"Record: {chunk_text[:1500]}\n\n"
            "Answer:"
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = (getattr(resp, "text", "") or "").strip().upper()
        verdict = "YES"
        if "NO" in raw and "YES" not in raw and "PARTIAL" not in raw:
            verdict = "NO"
        elif "PARTIAL" in raw:
            verdict = "PARTIAL"
        elif "YES" in raw:
            verdict = "YES"
        _REFLECT_CACHE[key] = verdict
        return verdict
    except Exception as e:  # noqa: BLE001
        logger.warning(f"reflect.failed: {e}")
        return "YES"  # fail-open


def _to_pgvector_literal(vec: list[float]) -> str:
    """Serialize a float list into pgvector's text literal form ``[a,b,c]``.

    pgvector는 list를 직접 받지 못하므로 문자열 리터럴로 캐스팅해 전달한다.
    """
    return "[" + ",".join(f"{v:.7f}" for v in vec) + "]"


# ---------------------------------------------------------------------------
# Mock Data Store
# AlloyDB + pgvector 없이 동작하도록 하드코딩된 테스트 데이터
# Hardcoded test data to operate without AlloyDB + pgvector
# ---------------------------------------------------------------------------

_MOCK_VISIT_RECORDS = [
    {
        "visit_id": "VIS-001",
        "patient_id": "patient_001",
        "visit_date": "2026-04-03",
        "doctor_name": "Dr. Sharma",
        "hospital_name": "City Hospital Mumbai",
        "structured_summary": (
            "Routine diabetes follow-up. BP 140/90, HR 78. HbA1c 7.2% (prev 7.5%). "
            "Metformin increased from 500mg to 1000mg twice daily. "
            "Advised sodium restriction and daily walking 30 min. "
            "Follow-up in 3 months. HbA1c blood test booked."
        ),
        "key_findings": {
            "blood_pressure": "140/90",
            "heart_rate": "78",
            "hba1c": "7.2%",
            "weight": "78kg",
        },
        "raw_input": (
            "Saw Dr. Sharma today at City Hospital. BP was 140 over 90. "
            "HbA1c came down to 7.2 from 7.5. Doctor increased Metformin to 1000mg. "
            "Told me to reduce salt and walk every day."
        ),
        "_keywords": [
            "blood pressure", "bp", "140/90", "hypertension",
            "hba1c", "diabetes", "metformin", "1000mg",
            "sodium", "salt", "walking", "exercise",
            "dr. sharma", "city hospital",
        ],
    },
    {
        "visit_id": "VIS-002",
        "patient_id": "patient_001",
        "visit_date": "2026-03-15",
        "doctor_name": "Dr. Patel",
        "hospital_name": "Apollo Hospital Bangalore",
        "structured_summary": (
            "Endocrinology consult. BP 135/85. HbA1c 7.5%. Fasting glucose 145. "
            "Started Amlodipine 5mg for hypertension. Discussed Atorvastatin side effects — "
            "patient tolerating well. Lipid panel ordered. Kidney function normal (eGFR 72)."
        ),
        "key_findings": {
            "blood_pressure": "135/85",
            "hba1c": "7.5%",
            "fasting_glucose": "145 mg/dL",
            "egfr": "72",
            "ldl": "pending",
        },
        "raw_input": (
            "Visited Dr. Patel at Apollo. BP 135/85. Sugar fasting was 145. "
            "He started me on Amlodipine 5mg for blood pressure. "
            "Kidney tests came back normal. Need to do lipid panel next time."
        ),
        "_keywords": [
            "blood pressure", "bp", "135/85", "hypertension", "amlodipine",
            "fasting glucose", "sugar", "145", "diabetes",
            "kidney", "egfr", "lipid", "cholesterol",
            "dr. patel", "apollo hospital",
        ],
    },
    {
        "visit_id": "VIS-003",
        "patient_id": "patient_001",
        "visit_date": "2026-02-10",
        "doctor_name": "Dr. Sharma",
        "hospital_name": "City Hospital Mumbai",
        "structured_summary": (
            "Routine follow-up. BP 145/92 — elevated. HbA1c 7.5%. "
            "Started Aspirin 75mg for cardiovascular prophylaxis. "
            "Atorvastatin 20mg continued. Advised weight loss (target 75kg from 80kg). "
            "Dietician referral given."
        ),
        "key_findings": {
            "blood_pressure": "145/92",
            "hba1c": "7.5%",
            "weight": "80kg",
        },
        "raw_input": (
            "Went to Dr. Sharma. BP high at 145/92. HbA1c same at 7.5. "
            "He started Aspirin 75mg. Told me to lose 5 kgs. "
            "Gave me a referral to a dietician."
        ),
        "_keywords": [
            "blood pressure", "bp", "145/92", "high", "hypertension",
            "hba1c", "diabetes", "aspirin", "cardiovascular",
            "weight", "lose weight", "dietician", "diet",
            "atorvastatin", "cholesterol",
            "dr. sharma", "city hospital",
        ],
    },
]

_MOCK_HEALTH_METRICS = [
    {"metric_id": "HM-001", "patient_id": "patient_001", "metric_type": "blood_pressure",
     "value_primary": 140, "value_secondary": 90, "unit": "mmHg",
     "measured_at": "2026-04-03", "source": "clinic"},
    {"metric_id": "HM-002", "patient_id": "patient_001", "metric_type": "blood_pressure",
     "value_primary": 135, "value_secondary": 85, "unit": "mmHg",
     "measured_at": "2026-03-15", "source": "clinic"},
    {"metric_id": "HM-003", "patient_id": "patient_001", "metric_type": "blood_pressure",
     "value_primary": 145, "value_secondary": 92, "unit": "mmHg",
     "measured_at": "2026-02-10", "source": "clinic"},
    {"metric_id": "HM-004", "patient_id": "patient_001", "metric_type": "blood_glucose",
     "value_primary": 140, "value_secondary": None, "unit": "mg/dL",
     "measured_at": "2026-04-03", "source": "clinic", "notes": "fasting"},
    {"metric_id": "HM-005", "patient_id": "patient_001", "metric_type": "blood_glucose",
     "value_primary": 145, "value_secondary": None, "unit": "mg/dL",
     "measured_at": "2026-03-15", "source": "clinic", "notes": "fasting"},
    {"metric_id": "HM-006", "patient_id": "patient_001", "metric_type": "blood_glucose",
     "value_primary": 155, "value_secondary": None, "unit": "mg/dL",
     "measured_at": "2026-02-10", "source": "clinic", "notes": "fasting"},
    {"metric_id": "HM-007", "patient_id": "patient_001", "metric_type": "weight",
     "value_primary": 78, "value_secondary": None, "unit": "kg",
     "measured_at": "2026-04-03", "source": "clinic"},
    {"metric_id": "HM-008", "patient_id": "patient_001", "metric_type": "weight",
     "value_primary": 80, "value_secondary": None, "unit": "kg",
     "measured_at": "2026-02-10", "source": "clinic"},
]

_MOCK_APPOINTMENTS = [
    {
        "appointment_id": "APT-101",
        "patient_id": "patient_001",
        "title": "Follow-up with Dr. Patel (Endocrinology)",
        "date": "2026-04-15",
        "time": "10:00",
        "location": "Apollo Hospital Bangalore",
        "notes": "Bring lipid panel results",
    },
    {
        "appointment_id": "APT-102",
        "patient_id": "patient_001",
        "title": "HbA1c Fasting Blood Test",
        "date": "2026-04-20",
        "time": "07:30",
        "location": "City Hospital Mumbai Lab",
        "notes": "FASTING REQUIRED: 8-12 hours before test",
    },
]

_MOCK_CAREGIVER = {
    "patient_001": {
        "caregiver_id": "CG-001",
        "name": "Priya Sharma",
        "relationship": "daughter",
        "email": "1wosxai@gmail.com",
        "phone": "+91-9876543210",
        "city": "Bangalore",
    },
}

# 자동 증가 ID 카운터 / Auto-increment ID counters
_NEXT_VISIT_ID = len(_MOCK_VISIT_RECORDS) + 1
_NEXT_INSIGHT_ID = 1
_NEXT_NOTIF_ID = 1


# ---------------------------------------------------------------------------
# Helper Functions
# 내부 유틸리티 함수 / Internal utility functions
# ---------------------------------------------------------------------------

def _get_next_visit_id() -> str:
    global _NEXT_VISIT_ID
    vid = f"VIS-{_NEXT_VISIT_ID:03d}"
    _NEXT_VISIT_ID += 1
    return vid


def _get_next_insight_id() -> str:
    global _NEXT_INSIGHT_ID
    iid = f"INS-{_NEXT_INSIGHT_ID:03d}"
    _NEXT_INSIGHT_ID += 1
    return iid


def _get_next_notif_id() -> str:
    global _NEXT_NOTIF_ID
    nid = f"NTF-{_NEXT_NOTIF_ID:03d}"
    _NEXT_NOTIF_ID += 1
    return nid


def _get_visit_records_from_state(tool_context: ToolContext) -> list:
    """state에서 방문 기록 로드 (없으면 mock 데이터 초기화).

    Load visit records from state (initialize with mock data if empty).
    """
    records = tool_context.state.get("visit_records")
    if records is None:
        records = [rec.copy() for rec in _MOCK_VISIT_RECORDS]
        tool_context.state["visit_records"] = records
    return records


def _simple_keyword_match(query: str, keywords: list[str]) -> float:
    """간단한 키워드 기반 유사도 점수 계산 (pgvector 대용).

    Simple keyword-based similarity scoring (substitute for pgvector).
    Returns a score between 0.0 and 1.0.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())
    matches = sum(1 for kw in keywords if kw in query_lower or kw in query_words)
    if not keywords:
        return 0.0
    return min(matches / max(len(keywords) * 0.3, 1), 1.0)


# ---------------------------------------------------------------------------
# Tool Functions
# 에이전트가 호출할 수 있는 도구 함수들
# Functions callable by the LLM agent via function-calling
# ---------------------------------------------------------------------------


def store_visit_record(
    patient_id: str,
    visit_date: str,
    summary: str,
    tool_context: ToolContext,
    doctor_name: Optional[str] = None,
    hospital_name: Optional[str] = None,
    key_findings: Optional[str] = None,
) -> dict:
    """Store a visit record in the patient's history.

    In production this inserts into AlloyDB with a vector embedding
    for pgvector semantic search.

    환자의 방문 기록을 저장합니다.

    Args:
        patient_id: Unique patient identifier.
        visit_date: Visit date in YYYY-MM-DD format.
        summary: Structured summary of the visit.
        tool_context: ADK ToolContext for state management.
        doctor_name: Name of the attending doctor.
        hospital_name: Name of the hospital or clinic.
        key_findings: JSON string of key findings.

    Returns:
        dict with "status", "visit_id", and stored record details.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    # 요약 텍스트를 임베딩해 pgvector 검색용 벡터 컬럼에 함께 저장한다.
    # task_type=RETRIEVAL_DOCUMENT (저장용 비대칭) + title 메타데이터.
    # Embed the summary so that downstream pgvector search can hit this row.
    # Use RETRIEVAL_DOCUMENT asymmetry and a title header for better recall.
    _title = f"{visit_date} — {doctor_name or 'Unknown'} ({hospital_name or 'Unknown'})"
    embedding_vec = _generate_embedding(
        summary,
        task_type="RETRIEVAL_DOCUMENT",
        title=_title,
    )
    embedding_literal = _to_pgvector_literal(embedding_vec) if embedding_vec else None

    sql = """INSERT INTO visit_records (
                 patient_id, visit_date, structured_summary, doctor_name,
                 hospital_name, key_findings, raw_input, embedding
             )
             VALUES (
                 :pid, :vdate, :summ, :doc, :hosp,
                 COALESCE(:kf::jsonb, '{}'::jsonb), :raw,
                 CASE WHEN :emb IS NULL THEN NULL ELSE CAST(:emb AS vector) END
             )
             RETURNING id"""
    db_rows = execute_write(sql, {
        "pid": patient_id, "vdate": visit_date, "summ": summary,
        "doc": doctor_name or "Unknown", "hosp": hospital_name or "Unknown",
        "kf": key_findings, "raw": summary,
        "emb": embedding_literal,
    })
    if db_rows:
        return {
            "status": "success",
            "source": "alloydb",
            "visit_id": str(db_rows[0]["id"]),
            "visit_date": visit_date,
            "doctor_name": doctor_name or "Unknown",
            "message": f"Visit record '{db_rows[0]['id']}' saved for {visit_date}.",
        }

    records = _get_visit_records_from_state(tool_context)

    visit_id = _get_next_visit_id()
    # 키워드 자동 추출 / Auto-extract keywords from summary
    keywords = [w.lower() for w in summary.split() if len(w) > 3]

    new_record = {
        "visit_id": visit_id,
        "patient_id": patient_id,
        "visit_date": visit_date,
        "doctor_name": doctor_name or "Unknown",
        "hospital_name": hospital_name or "Unknown",
        "structured_summary": summary,
        "key_findings": key_findings or "{}",
        "raw_input": summary,
        "_keywords": keywords,
    }
    records.append(new_record)
    tool_context.state["visit_records"] = records

    return {
        "status": "success",
        "source": "mock",
        "visit_id": visit_id,
        "visit_date": visit_date,
        "doctor_name": doctor_name or "Unknown",
        "message": f"Visit record '{visit_id}' saved for {visit_date}.",
    }


def _log_search(tool_context: ToolContext, query: str, source: str) -> None:
    """Append a search entry to ``tool_context.state['search_log']``."""
    search_log = tool_context.state.get("search_log", []) if tool_context else []
    search_log.append({
        "query": query,
        "source": source,
        "searched_at": datetime.now().isoformat(),
    })
    if tool_context is not None:
        tool_context.state["search_log"] = search_log


def _format_vector_row(row: dict) -> dict:
    """Normalize a pgvector result row for the tool response envelope."""
    visit_date = row.get("visit_date")
    if hasattr(visit_date, "isoformat"):
        visit_date = visit_date.isoformat()
    similarity = row.get("similarity")
    try:
        similarity = round(float(similarity), 4) if similarity is not None else None
    except (TypeError, ValueError):
        similarity = None
    return {
        "visit_id": str(row.get("id", row.get("visit_id", ""))),
        "visit_date": visit_date,
        "doctor_name": row.get("doctor_name"),
        "hospital_name": row.get("hospital_name"),
        "summary": row.get("structured_summary") or row.get("summary"),
        "key_findings": row.get("key_findings"),
        "similarity_score": similarity,
    }


def _fallback_keyword_search(
    patient_id: str,
    query: str,
    top_k: int,
    tool_context: ToolContext,
) -> dict:
    """Keyword/ILIKE fallback used when embeddings are unavailable.

    임베딩 생성이나 pgvector 검색이 실패할 때 사용되는 fallback 경로.
    1) AlloyDB가 있으면 ILIKE 질의, 2) 없으면 mock 데이터 키워드 매칭.
    """
    # --- AlloyDB ILIKE path -------------------------------------------------
    sql = """SELECT id, visit_date, doctor_name, hospital_name,
                    structured_summary, key_findings
             FROM visit_records
             WHERE patient_id = :pid
               AND (structured_summary ILIKE :q OR key_findings::text ILIKE :q)
             ORDER BY visit_date DESC
             LIMIT :lim"""
    db_rows = query_dict(sql, {"pid": patient_id, "q": f"%{query}%", "lim": top_k})
    if db_rows:
        results = [_format_vector_row(r) for r in db_rows]
        return {
            "status": "success",
            "source": "alloydb_keyword",
            "query": query,
            "results_count": len(results),
            "top_similarity": None,
            "results": results,
            "records": results,  # alias for Agentic RAG spec
        }

    # --- Mock data path -----------------------------------------------------
    records = _get_visit_records_from_state(tool_context)
    patient_records = [r for r in records if r.get("patient_id") == patient_id]

    scored = []
    for record in patient_records:
        keywords = record.get("_keywords", [])
        score = _simple_keyword_match(query, keywords)
        if score > 0.0:
            scored.append({
                "visit_id": record["visit_id"],
                "visit_date": record["visit_date"],
                "doctor_name": record["doctor_name"],
                "hospital_name": record["hospital_name"],
                "summary": record["structured_summary"],
                "similarity_score": round(score, 2),
            })
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    results = scored[:top_k]

    return {
        "status": "success",
        "source": "mock_keyword",
        "query": query,
        "results_count": len(results),
        "top_similarity": results[0]["similarity_score"] if results else None,
        "results": results,
        "records": results,
    }


def search_medical_history(
    patient_id: str,
    query: str,
    tool_context: ToolContext,
    top_k: int = 5,
    similarity_threshold: float = 0.6,
) -> dict:
    """Agentic RAG search over a patient's visit history.

    방문 기록에 대한 Agentic RAG 검색:
        1) 질의 텍스트를 Gemini text-embedding-004로 임베딩한다.
        2) pgvector ``<=>`` 연산자로 코사인 거리 기반 top-k를 조회한다.
        3) 최상위 유사도가 임계치(``similarity_threshold``)를 넘지 못하면
           ``insufficient_results`` 상태를 반환해 에이전트가 질의를 재구성
           하도록 유도한다 (multi-hop / iterative retrieval).
        4) 임베딩 또는 pgvector 경로가 실패하면 키워드 fallback으로 떨어진다.

    Args:
        patient_id: Unique patient identifier.
        query: Natural language search query.
        tool_context: ADK ToolContext for state management.
        top_k: Max number of records to return (default 5).
        similarity_threshold: Cosine similarity cutoff (0-1) below which the
            results are considered insufficient and the caller is asked to
            reformulate the query. Default 0.6.

    Returns:
        A dict envelope with ``status`` in
        ``{"success", "insufficient_results", "no_results"}``, plus
        ``query``, ``source``, ``top_similarity``, ``results_count``,
        ``results`` and ``records`` (alias).
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    _log_search(tool_context, query, source="vector")

    # --- Step 1: query embedding -------------------------------------------
    # task_type=RETRIEVAL_QUERY 비대칭 — 쿼리와 문서를 같은 task_type으로 임베딩하면
    # recall 25-30% 손실 (Dr. Chandra). Query-side에선 반드시 QUERY를 써야 한다.
    query_emb = _generate_embedding(query, task_type="RETRIEVAL_QUERY")
    if query_emb is None:
        # 임베딩 실패 → 키워드 fallback. 에이전트 관점에선 여전히 결과를
        # 받아볼 수 있으므로 세션이 죽지 않는다.
        logger.info("rag.embedding_unavailable — falling back to keyword search")
        return _fallback_keyword_search(patient_id, query, top_k, tool_context)

    # --- Step 2: pgvector cosine similarity --------------------------------
    emb_literal = _to_pgvector_literal(query_emb)
    vector_sql = """
        SELECT id,
               visit_date,
               doctor_name,
               hospital_name,
               structured_summary,
               key_findings,
               1 - (embedding <=> CAST(:query_emb AS vector)) AS similarity
        FROM visit_records
        WHERE patient_id = :pid
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query_emb AS vector)
        LIMIT :k
    """
    db_rows = query_dict(vector_sql, {
        "pid": patient_id,
        "query_emb": emb_literal,
        "k": top_k,
    })

    # query_dict가 빈 리스트를 반환하는 경우는 두 가지다:
    #   (a) AlloyDB 미설정 → mock fallback 필요
    #   (b) 실제 DB에 해당 환자의 임베딩 레코드가 없음
    # (a)와 (b)를 구별하기 위해 engine 상태를 직접 확인한다.
    if not db_rows:
        from careflow.db.alloydb_client import get_db_engine
        if get_db_engine() is None:
            return _fallback_keyword_search(patient_id, query, top_k, tool_context)
        # 엔진은 있는데 결과가 비었다 — 완전 무결과
        return {
            "status": "no_results",
            "source": "pgvector",
            "query": query,
            "top_similarity": None,
            "results_count": 0,
            "results": [],
            "records": [],
            "suggestion": (
                "No vector matches found. Reformulate with medical synonyms "
                "or broader clinical terms and retry."
            ),
        }

    # --- Step 3: Agentic reasoning on result quality -----------------------
    formatted = [_format_vector_row(r) for r in db_rows]
    top_similarity = formatted[0]["similarity_score"] or 0.0

    if top_similarity >= similarity_threshold:
        # 재구성 카운터를 리셋 — 성공 경로.
        if tool_context is not None:
            tool_context.state["rag_iteration_count"] = 0
        return {
            "status": "success",
            "source": "pgvector",
            "query": query,
            "top_similarity": top_similarity,
            "results_count": len(formatted),
            "results": formatted,
            "records": formatted,
        }

    # --- Step 4: insufficient → nudge the agent to reformulate -------------
    if tool_context is not None:
        iter_count = tool_context.state.get("rag_iteration_count", 0)
        tool_context.state["rag_iteration_count"] = iter_count + 1

    return {
        "status": "insufficient_results",
        "source": "pgvector",
        "query": query,
        "top_similarity": top_similarity,
        "similarity_threshold": similarity_threshold,
        "results_count": len(formatted),
        "results": formatted,
        "records": formatted,
        "suggestion": (
            "Top similarity below threshold. Reformulate the query using "
            "medical synonyms (e.g. 'chest pain' -> 'angina'), broader "
            "clinical terms, or related concepts, then call "
            "search_medical_history again."
        ),
    }


def semantic_search_with_reformulation(
    patient_id: str,
    original_query: str,
    tool_context: ToolContext,
    max_attempts: int = 3,
    similarity_threshold: float = 0.6,
) -> dict:
    """Multi-hop Agentic RAG driver.

    단일 검색만으로 충분한 근거를 얻지 못할 때, 간단한 휴리스틱 기반
    재질의를 반복해 최적 결과를 찾는 래퍼 함수.
    LoopAgent 없이 프롬프트 또는 에이전트가 직접 호출할 수 있다.

    LLM이 직접 재질의를 제안하는 경우에는 이 함수 대신 search_medical_history
    를 원하는 질의로 여러 번 호출하는 것을 권장한다. 이 함수는 결정적
    fallback 루프를 제공하기 위한 것이다.

    Args:
        patient_id: Unique patient identifier.
        original_query: The user's original natural-language query.
        tool_context: ADK ToolContext — used for state tracking and logging.
        max_attempts: Maximum number of (reformulated) retrieval attempts.
        similarity_threshold: Cosine similarity cutoff that counts as success.

    Returns:
        A dict with the best attempt's results plus an ``attempts`` trace
        showing each query variant tried and its top similarity.
    """
    # 의학 동의어 — 시연·테스트용 휴리스틱 매핑. 운영에서는 UMLS/SNOMED 매핑
    # 또는 LLM 기반 재질의로 교체한다.
    # Toy medical synonym map for demo/testing. In production replace with
    # UMLS/SNOMED mapping or an LLM-driven rewriter.
    # 45+ mappings — Dr. Mehrotra clinical guide 반영.
    # Covers symptoms, labs, conditions, DM2+HTN full drug classes, adherence.
    _SYNONYMS = {
        # ── Symptoms ──
        "chest pain": ["angina", "cardiac discomfort", "retrosternal pain"],
        "shortness of breath": ["dyspnea", "breathlessness", "respiratory distress"],
        "dizziness": ["vertigo", "lightheadedness", "presyncope"],
        "headache": ["cephalalgia", "migraine", "tension headache"],
        "nausea": ["emesis", "vomiting", "nausea and vomiting"],
        "fatigue": ["lethargy", "malaise", "tiredness"],
        "swelling": ["edema", "oedema", "peripheral edema"],
        "numbness": ["neuropathy", "paresthesia", "tingling"],
        "blurred vision": ["visual disturbance", "retinopathy", "visual acuity"],
        "frequent urination": ["polyuria", "urinary frequency", "nocturia"],
        "excessive thirst": ["polydipsia", "increased thirst"],
        # ── Labs / Vitals ──
        "blood sugar": ["glucose level", "glycemia", "hba1c", "fasting glucose"],
        "blood pressure": ["bp", "hypertension", "systolic diastolic"],
        "high blood pressure": ["hypertension", "elevated bp", "htn"],
        "heart rate": ["pulse", "hr", "tachycardia", "bradycardia"],
        "cholesterol": ["lipid panel", "ldl", "hdl", "statin", "triglycerides"],
        "kidney function": ["renal function", "egfr", "creatinine", "bun"],
        "liver function": ["hepatic panel", "alt", "ast", "bilirubin"],
        "thyroid": ["tsh", "t3", "t4", "thyroid function"],
        "urine test": ["urinalysis", "microalbuminuria", "urine protein"],
        "weight": ["body mass", "bmi", "obesity", "body weight"],
        # ── Conditions ──
        "diabetes": ["type 2 diabetes", "dm2", "hyperglycemia", "insulin resistance"],
        "heart disease": ["cardiovascular disease", "cad", "coronary artery disease"],
        "stroke": ["cerebrovascular accident", "cva", "tia"],
        "heart failure": ["chf", "congestive heart failure", "cardiac insufficiency"],
        "nerve damage": ["neuropathy", "peripheral neuropathy", "diabetic neuropathy"],
        "eye problems": ["retinopathy", "diabetic retinopathy", "macular edema"],
        # ── DM2 Medications ──
        "metformin": ["glucophage", "glyciphage", "glycomet", "biguanide"],
        "glipizide": ["glucotrol", "sulfonylurea", "glimepiride", "glyburide"],
        "sitagliptin": ["januvia", "dpp-4 inhibitor", "dpp4i", "vildagliptin"],
        "empagliflozin": ["jardiance", "sglt2 inhibitor", "dapagliflozin", "canagliflozin"],
        "liraglutide": ["victoza", "glp-1 agonist", "semaglutide", "ozempic"],
        "insulin": ["insulin glargine", "lantus", "insulin aspart", "novorapid"],
        # ── HTN Medications ──
        "amlodipine": ["norvasc", "calcium channel blocker", "ccb", "nifedipine"],
        "lisinopril": ["ace inhibitor", "acei", "enalapril", "ramipril"],
        "losartan": ["arb", "angiotensin receptor blocker", "valsartan", "telmisartan"],
        "atenolol": ["beta blocker", "metoprolol", "carvedilol", "propranolol"],
        "hydrochlorothiazide": ["hctz", "thiazide", "diuretic", "chlorthalidone"],
        "aspirin": ["acetylsalicylic acid", "asa", "antiplatelet"],
        "atorvastatin": ["lipitor", "statin", "rosuvastatin", "simvastatin"],
        # ── Adherence / Behavior ──
        "heart medication": ["cardiovascular drugs", "antihypertensive", "cardiac drugs"],
        "forgot medicine": ["missed dose", "non-adherent", "skipped medication"],
        "salt": ["sodium", "sodium restriction", "low salt diet", "dash diet"],
        "exercise": ["physical activity", "walking", "aerobic exercise"],
        "diet": ["nutrition", "meal plan", "dietary intake", "caloric intake"],
    }

    def _reformulate(q: str, attempt: int) -> str:
        q_lower = q.lower()
        for key, alts in _SYNONYMS.items():
            if key in q_lower and attempt - 1 < len(alts):
                return q_lower.replace(key, alts[attempt - 1])
        # 일반 폴백: 첫 시도 실패면 더 넓은 상위 개념으로 축약한다.
        # Generic fallback: broaden by keeping only the longest meaningful token.
        tokens = [t for t in q_lower.split() if len(t) > 3]
        if not tokens:
            return q
        return tokens[-1]

    attempts_trace: list[dict] = []
    best_result: dict | None = None
    best_similarity = -1.0

    current_query = original_query
    for attempt in range(1, max_attempts + 1):
        result = search_medical_history(
            patient_id=patient_id,
            query=current_query,
            tool_context=tool_context,
            similarity_threshold=similarity_threshold,
        )
        top_sim = result.get("top_similarity") or 0.0
        attempts_trace.append({
            "attempt": attempt,
            "query": current_query,
            "status": result.get("status"),
            "top_similarity": top_sim,
            "results_count": result.get("results_count", 0),
        })

        if top_sim > best_similarity:
            best_similarity = top_sim
            best_result = result

        if result.get("status") == "success":
            break

        # Reformulate for the next round.
        current_query = _reformulate(original_query, attempt)

    if best_result is None:
        best_result = {
            "status": "no_results",
            "source": "pgvector",
            "query": original_query,
            "results": [],
            "records": [],
        }

    return {
        **best_result,
        "original_query": original_query,
        "attempts": attempts_trace,
        "final_status": best_result.get("status"),
    }


# ---------------------------------------------------------------------------
# S-tier Agentic RAG — HyDE + Hybrid (Dense + BM25) + RRF + Self-RAG
# 최상위 통합 파이프라인
# ---------------------------------------------------------------------------


def _dense_vector_candidates(
    patient_id: str,
    query_emb_literal: str,
    top_k: int,
) -> list[dict]:
    """Dense vector retrieval leg of the hybrid search.

    Returns pgvector cosine top-k candidates (may be empty if no AlloyDB).
    """
    sql = """
        SELECT id, visit_date, doctor_name, hospital_name,
               structured_summary, key_findings,
               1 - (embedding <=> CAST(:q AS vector)) AS similarity
        FROM visit_records
        WHERE patient_id = :pid AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:q AS vector)
        LIMIT :k
    """
    return query_dict(sql, {"pid": patient_id, "q": query_emb_literal, "k": top_k})


def _lexical_bm25_candidates(
    patient_id: str,
    query: str,
    top_k: int,
) -> list[dict]:
    """Lexical (BM25-ish) retrieval via PostgreSQL full-text search.

    ``ts_rank_cd`` over a ``plainto_tsquery`` of the user query — catches
    proper nouns, drug names, numeric tokens that dense embeddings miss
    (e.g., "Metformin 1000mg", "BP 140/90").

    Uses ``plainto_tsquery`` (not ``to_tsquery``) so that arbitrary user
    input is safely tokenized without blowing up on `&` / `|` / `!` chars.
    """
    sql = """
        SELECT id, visit_date, doctor_name, hospital_name,
               structured_summary, key_findings,
               ts_rank_cd(
                   to_tsvector('english',
                       coalesce(structured_summary,'') || ' ' || coalesce(raw_input,'')),
                   plainto_tsquery('english', :q)
               ) AS lex_score
        FROM visit_records
        WHERE patient_id = :pid
          AND to_tsvector('english',
                coalesce(structured_summary,'') || ' ' || coalesce(raw_input,''))
              @@ plainto_tsquery('english', :q)
        ORDER BY lex_score DESC
        LIMIT :k
    """
    try:
        return query_dict(sql, {"pid": patient_id, "q": query, "k": top_k})
    except Exception as e:  # noqa: BLE001
        # plainto_tsquery 는 빈 질의에 대해 empty tsquery를 반환하므로 보통 실패하지 않지만,
        # 혹시 모를 DB-side 에러는 조용히 빈 리스트로 처리해 파이프라인을 계속 살린다.
        logger.warning(f"lexical_search.failed: {e}")
        return []


def _reciprocal_rank_fusion(
    dense_rows: list[dict],
    lexical_rows: list[dict],
    k_rrf: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion of two candidate lists.

    RRF score = sum over sources of 1 / (k + rank).
    k=60 is the standard default from Cormack et al. (2009).
    Returns the fused list ordered by RRF score desc, carrying both
    ``similarity`` (dense) and ``lex_score`` (lexical) where available.
    """
    by_id: dict = {}

    for rank, row in enumerate(dense_rows, start=1):
        rid = str(row["id"])
        entry = by_id.setdefault(rid, dict(row))
        entry["rrf_score"] = entry.get("rrf_score", 0.0) + 1.0 / (k_rrf + rank)
        entry["_dense_rank"] = rank

    for rank, row in enumerate(lexical_rows, start=1):
        rid = str(row["id"])
        entry = by_id.setdefault(rid, dict(row))
        entry["rrf_score"] = entry.get("rrf_score", 0.0) + 1.0 / (k_rrf + rank)
        entry["_lex_rank"] = rank
        # Carry lex_score and fill dense similarity only if absent.
        if "lex_score" in row:
            entry["lex_score"] = row["lex_score"]

    fused = list(by_id.values())
    fused.sort(key=lambda r: r.get("rrf_score", 0.0), reverse=True)
    return fused


def agentic_rag_search(
    patient_id: str,
    query: str,
    tool_context: ToolContext,
    top_k: int = 5,
    use_hyde: bool = True,
    use_reflection: bool = True,
    similarity_threshold: float = 0.6,
) -> dict:
    """S-tier Agentic RAG pipeline — HyDE + Hybrid + RRF + Self-RAG.

    Pipeline:
      1. **HyDE** — Gemini Flash drafts a hypothetical clinical note answering
         the query; we embed that draft with ``RETRIEVAL_QUERY`` to bridge the
         lay ↔ clinical vocabulary gap. Raw-query embedding is used as fallback.
      2. **Hybrid retrieval** — run pgvector cosine (dense) and PostgreSQL
         ``ts_rank_cd`` (lexical/BM25-ish) in parallel.
      3. **RRF fusion** — merge with Reciprocal Rank Fusion (k=60).
      4. **Self-RAG reflection** — Gemini Flash judges each fused candidate as
         YES/PARTIAL/NO for the original query. Only YES/PARTIAL pass through.
      5. **Groundedness envelope** — returns retrieval trace + evidence list
         so downstream LLM synthesis can cite sources.

    Failure-modes: any sub-step failure degrades gracefully — HyDE miss falls
    back to raw query embed; BM25 miss falls back to dense-only; reflection
    failure falls back to YES (fail-open). The pipeline never silently returns
    a mock result when AlloyDB is available.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    trace: dict = {
        "query": query,
        "use_hyde": use_hyde,
        "use_reflection": use_reflection,
        "steps": [],
    }
    _log_search(tool_context, query, source="agentic_rag")

    # --- Step 1: HyDE query expansion --------------------------------------
    hypo = _hyde_generate_hypothetical(query) if use_hyde else None
    if hypo:
        embed_text = f"{query}\n\n{hypo}"  # concat raw query + hypothetical
        trace["steps"].append({"step": "hyde", "status": "ok", "hypo_chars": len(hypo)})
    else:
        embed_text = query
        trace["steps"].append({"step": "hyde", "status": "skipped"})

    query_emb = _generate_embedding(embed_text, task_type="RETRIEVAL_QUERY")
    if query_emb is None:
        logger.info("agentic_rag.embedding_unavailable — keyword fallback")
        fb = _fallback_keyword_search(patient_id, query, top_k, tool_context)
        fb["retrieval_trace"] = trace
        return fb

    emb_literal = _to_pgvector_literal(query_emb)

    # --- Step 2: Hybrid retrieval (dense + lexical) ------------------------
    # Over-fetch 2x top_k per leg so RRF has headroom to promote cross-hits.
    fetch_k = max(top_k * 2, 10)
    dense_rows = _dense_vector_candidates(patient_id, emb_literal, fetch_k)

    # engine 존재 여부 판정 — "DB 없음"과 "쿼리 결과 없음" 구별.
    from careflow.db.alloydb_client import get_db_engine
    if get_db_engine() is None:
        logger.info("agentic_rag.no_engine — keyword fallback")
        fb = _fallback_keyword_search(patient_id, query, top_k, tool_context)
        fb["retrieval_trace"] = trace
        return fb

    lex_rows = _lexical_bm25_candidates(patient_id, query, fetch_k)
    trace["steps"].append({
        "step": "hybrid_retrieve",
        "dense_hits": len(dense_rows),
        "lexical_hits": len(lex_rows),
    })

    # --- Step 3: RRF fusion ------------------------------------------------
    fused = _reciprocal_rank_fusion(dense_rows, lex_rows, k_rrf=60)
    trace["steps"].append({"step": "rrf_fusion", "fused_count": len(fused)})
    if not fused:
        return {
            "status": "no_results",
            "source": "agentic_rag",
            "query": query,
            "results": [],
            "records": [],
            "retrieval_trace": trace,
            "suggestion": (
                "Neither dense nor lexical retrieval returned any rows. "
                "Verify patient_id and that visit_records exist + are embedded."
            ),
        }

    # --- Step 3.5: Cross-patient post-retrieval assertion --------------------
    # Dr. Mehrotra: query-time WHERE 필터 만으로는 insufficient. post-retrieval에서
    # 한 번 더 검증해 cross-patient data leak을 방어한다 (defense-in-depth).
    pre_filter_count = len(fused)
    fused = [r for r in fused if str(r.get("patient_id", patient_id)) == str(patient_id)]
    leaked = pre_filter_count - len(fused)
    if leaked > 0:
        logger.warning(
            "agentic_rag.cross_patient_leak_blocked count=%d patient=%s",
            leaked, patient_id,
        )
    trace["steps"].append({
        "step": "cross_patient_assertion",
        "pre_filter": pre_filter_count,
        "leaked_blocked": leaked,
    })

    # --- Step 4: Self-RAG reflection ---------------------------------------
    top_fused = fused[:fetch_k]
    reflected: list[dict] = []
    reflect_counts = {"YES": 0, "PARTIAL": 0, "NO": 0}
    for row in top_fused:
        chunk_text = row.get("structured_summary") or ""
        if use_reflection:
            verdict = _reflect_chunk_relevance(query, chunk_text)
        else:
            verdict = "YES"
        reflect_counts[verdict] = reflect_counts.get(verdict, 0) + 1
        if verdict == "NO":
            continue
        formatted = _format_vector_row(row)
        formatted["rrf_score"] = round(float(row.get("rrf_score", 0.0)), 6)
        formatted["dense_rank"] = row.get("_dense_rank")
        formatted["lex_rank"] = row.get("_lex_rank")
        formatted["reflection"] = verdict
        reflected.append(formatted)

    trace["steps"].append({"step": "self_rag_reflection", **reflect_counts})

    # If reflection rejected everything, fall back to raw fused top-k so we
    # never return an empty list while rows actually existed.
    if not reflected:
        logger.info("agentic_rag.reflection_rejected_all — returning raw fused")
        reflected = []
        for row in top_fused[:top_k]:
            f = _format_vector_row(row)
            f["rrf_score"] = round(float(row.get("rrf_score", 0.0)), 6)
            f["reflection"] = "NO-overridden"
            reflected.append(f)

    reflected = reflected[:top_k]
    top_similarity = max(
        (r.get("similarity_score") or 0.0) for r in reflected
    ) if reflected else 0.0

    # --- Step 5: Confidence tiering (Dr. Mehrotra) -------------------------
    # High ≥ 0.78  — strong match, cite directly
    # Medium 0.6~0.78 — plausible, include but note lower confidence
    # Low < 0.6 — refuse to cite, suggest reformulation
    if top_similarity >= 0.78:
        confidence = "HIGH"
        status = "success"
    elif top_similarity >= similarity_threshold:
        confidence = "MEDIUM"
        status = "success"
    else:
        confidence = "LOW"
        status = "low_confidence"

    if tool_context is not None and status == "success":
        tool_context.state["rag_iteration_count"] = 0

    trace["steps"].append({
        "step": "confidence_tiering",
        "top_similarity": round(top_similarity, 4),
        "confidence": confidence,
    })

    result_envelope = {
        "status": status,
        "source": "agentic_rag",
        "query": query,
        "top_similarity": round(top_similarity, 4),
        "confidence": confidence,
        "results_count": len(reflected),
        "results": reflected,
        "records": reflected,
        "retrieval_trace": trace,
    }

    if confidence == "LOW":
        result_envelope["suggestion"] = (
            "Retrieval confidence is LOW (top similarity < 0.6). "
            "Results should NOT be cited as evidence. Reformulate with "
            "medical synonyms or broader terms, or tell the patient "
            "that no matching records were found."
        )

    return result_envelope


def get_upcoming_appointments(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve all upcoming appointments for a patient.

    환자의 예정된 모든 예약 목록을 반환합니다.

    Args:
        patient_id: Unique patient identifier.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "appointment_count", and "appointments" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    sql = "SELECT * FROM appointments WHERE patient_id = :pid AND status = 'scheduled' ORDER BY scheduled_date"
    db_rows = query_dict(sql, {"pid": patient_id})
    if db_rows:
        for tuple_row in db_rows:
            if hasattr(tuple_row.get("scheduled_date"), "isoformat"):
                tuple_row["date"] = tuple_row["scheduled_date"].strftime("%Y-%m-%d")
                tuple_row["time"] = tuple_row["scheduled_date"].strftime("%H:%M")
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "appointment_count": len(db_rows),
            "appointments": db_rows,
        }

    # state에서 예약 로드 또는 mock 사용 / Load from state or use mocks
    appointments = tool_context.state.get("medical_info_appointments")
    if appointments is None:
        appointments = [apt.copy() for apt in _MOCK_APPOINTMENTS]
        tool_context.state["medical_info_appointments"] = appointments

    patient_apts = [
        apt for apt in appointments
        if apt.get("patient_id") == patient_id
    ]
    patient_apts.sort(key=lambda a: (a["date"], a["time"]))

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "appointment_count": len(patient_apts),
        "appointments": patient_apts,
    }


def get_health_metrics(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve all health metrics for a patient.

    환자의 전체 건강 지표를 반환합니다.

    Args:
        patient_id: Unique patient identifier.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "metric_count", and "metrics" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    sql = "SELECT * FROM health_metrics WHERE patient_id = :pid ORDER BY measured_at DESC"
    db_rows = query_dict(sql, {"pid": patient_id})
    if db_rows:
        for r in db_rows:
            if hasattr(r.get("measured_at"), "isoformat"):
                r["measured_at"] = r["measured_at"].isoformat()
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "metric_count": len(db_rows),
            "metrics": db_rows,
        }

    metrics = tool_context.state.get("health_metrics")
    if metrics is None:
        metrics = [m.copy() for m in _MOCK_HEALTH_METRICS]
        tool_context.state["health_metrics"] = metrics

    patient_metrics = [
        m for m in metrics if m.get("patient_id") == patient_id
    ]
    patient_metrics.sort(key=lambda m: m.get("measured_at", ""), reverse=True)

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "metric_count": len(patient_metrics),
        "metrics": patient_metrics,
    }


def get_health_metrics_by_type(
    patient_id: str,
    metric_type: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve health metrics for a patient filtered by type.

    특정 유형의 건강 지표만 필터링하여 반환합니다.

    Args:
        patient_id: Unique patient identifier.
        metric_type: Type — "blood_pressure", "blood_glucose", "weight", "heart_rate".
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "metric_type", "metric_count", and "metrics" list.
    """
    all_result = get_health_metrics(patient_id, tool_context)
    filtered = [
        m for m in all_result["metrics"]
        if m.get("metric_type") == metric_type
    ]

    return {
        "status": "success",
        "source": all_result.get("source", "mock"),
        "patient_id": patient_id,
        "metric_type": metric_type,
        "metric_count": len(filtered),
        "metrics": filtered,
    }


def save_health_insight(
    patient_id: str,
    insight_type: str,
    title: str,
    content: str,
    tool_context: ToolContext,
    severity: str = "info",
) -> dict:
    """Store a generated health insight for a patient.

    환자에 대한 건강 인사이트를 저장합니다.

    Args:
        patient_id: Unique patient identifier.
        insight_type: Type — "trend_alert", "correlation", "pre_visit_summary", "recommendation".
        title: Short descriptive title.
        content: Full insight text.
        tool_context: ADK ToolContext for state management.
        severity: Severity — "info", "warning", or "urgent".

    Returns:
        dict with "status", "insight_id", and created insight details.
    """
    sql = """INSERT INTO health_insights (patient_id, insight_type, severity, title, content)
             VALUES (:pid, :itype, :sev, :tit, :con)
             RETURNING id"""
    db_rows = execute_write(sql, {
        "pid": patient_id, "itype": insight_type, "sev": severity,
        "tit": title, "con": content
    })
    if db_rows:
        return {
            "status": "success",
            "source": "alloydb",
            "insight_id": str(db_rows[0]["id"]),
            "insight_type": insight_type,
            "severity": severity,
            "title": title,
            "message": f"Health insight '{title}' saved ({severity}).",
        }

    insights = tool_context.state.get("health_insights", [])

    insight_id = _get_next_insight_id()
    new_insight = {
        "insight_id": insight_id,
        "patient_id": patient_id,
        "insight_type": insight_type,
        "severity": severity,
        "title": title,
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    insights.append(new_insight)
    tool_context.state["health_insights"] = insights

    return {
        "status": "success",
        "source": "mock",
        "insight_id": insight_id,
        "insight_type": insight_type,
        "severity": severity,
        "title": title,
        "message": f"Health insight '{title}' saved ({severity}).",
    }


def send_caregiver_notification(
    patient_id: str,
    notification_type: str,
    subject: str,
    message: str,
    tool_context: ToolContext,
) -> dict:
    """Send a notification to the patient's caregiver.

    In production this sends via Gmail SMTP / Twilio.
    Here it logs to state for demo purposes.

    환자의 보호자에게 알림을 전송합니다.

    Args:
        patient_id: Unique patient identifier.
        notification_type: Type — "VISIT_UPDATE", "WEEKLY_DIGEST", "ALERT", "MEDICATION_REMINDER".
        subject: Notification subject line.
        message: The notification message body.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "notification_id", and delivery details.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    sql = """INSERT INTO notifications (patient_id, caregiver_id, type, delivery_method, content, status)
             VALUES (:pid, (SELECT caregiver_id FROM patients WHERE id = :pid LIMIT 1),
                     :ntype, 'email', :con::jsonb, 'sent')
             RETURNING id, (SELECT name FROM caregivers c WHERE c.id = (SELECT caregiver_id FROM patients WHERE id = :pid LIMIT 1)) as cg_name"""
    db_rows = execute_write(sql, {
        "pid": patient_id, "ntype": notification_type,
        "con": json.dumps({"subject": subject, "body": message})
    })
    if db_rows:
        return {
            "status": "success",
            "source": "alloydb",
            "notification_id": str(db_rows[0]["id"]),
            "caregiver_name": db_rows[0].get("cg_name", "Unknown"),
            "notification_type": notification_type,
            "delivery_status": "sent (mock config)",
            "message": f"Notification sent to {db_rows[0].get('cg_name', 'Unknown')}: [{notification_type}] {subject}",
        }

    notif_log = tool_context.state.get("notification_log", [])

    notif_id = _get_next_notif_id()
    caregiver = _MOCK_CAREGIVER.get(patient_id, {})

    entry = {
        "notification_id": notif_id,
        "patient_id": patient_id,
        "caregiver_name": caregiver.get("name", "Unknown"),
        "notification_type": notification_type,
        "subject": subject,
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "delivery_status": "sent (mock)",
        "sent_at": datetime.now().isoformat(),
    }
    notif_log.append(entry)
    tool_context.state["notification_log"] = notif_log

    return {
        "status": "success",
        "source": "mock",
        "notification_id": notif_id,
        "caregiver_name": caregiver.get("name", "Unknown"),
        "notification_type": notification_type,
        "delivery_status": "sent (mock)",
        "message": (
            f"Notification sent to {caregiver.get('name', 'caregiver')}: "
            f"[{notification_type}] {subject}"
        ),
    }


def get_caregiver_info(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve the caregiver information for a patient.

    환자의 보호자 정보를 조회합니다.

    Args:
        patient_id: Unique patient identifier.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status" and caregiver details (name, relationship, contact info).
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    sql = """SELECT c.* FROM caregivers c
             JOIN patients p ON p.caregiver_id = c.id
             WHERE p.id = :pid"""
    db_rows = query_dict(sql, {"pid": patient_id})
    if db_rows:
        c = dict(db_rows[0])
        c["id"] = str(c["id"])
        c["created_at"] = str(c["created_at"]) if c.get("created_at") else None
        return {
            "status": "found",
            "source": "alloydb",
            **c
        }

    caregiver = _MOCK_CAREGIVER.get(patient_id)
    if caregiver:
        return {
            "status": "found",
            "source": "mock",
            **caregiver,
        }

    return {
        "status": "not_found",
        "patient_id": patient_id,
        "message": f"No caregiver registered for patient '{patient_id}'.",
    }
