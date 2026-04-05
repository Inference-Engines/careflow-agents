"""
Symptom Triage Agent — Tool Definitions
증상 분류 에이전트 — 도구 정의

FunctionTool implementations for the Symptom Triage Agent.
Each tool uses mock data for local development and testing.
각 도구는 로컬 개발/테스트를 위한 mock 데이터를 사용합니다.

Production note / 프로덕션 참고:
  실제 배포 시 mock 데이터를 MCP Toolbox for Databases (AlloyDB) 연동으로 교체합니다.
  In production, replace mock data with MCP Toolbox for Databases (AlloyDB) integration.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

from google.adk.tools.tool_context import ToolContext

# AlloyDB 우선 조회용 공용 헬퍼 / Shared helper for AlloyDB-first lookups
from careflow.db.alloydb_client import query_dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API 설정 / API Configuration
# ---------------------------------------------------------------------------
_API_TIMEOUT = 5  # 초 / seconds

# SSL 컨텍스트 — 일부 환경에서 인증서 문제 우회 / SSL context for cert issues
_SSL_CTX = ssl.create_default_context()
try:
    _SSL_CTX.load_default_certs()
except Exception:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE


# ──────────────────────────────────────────────────────────────────────
# ICD-11 mapping path — datasets/official_icd11/icd11_careflow_mapping.json
# ICD-11 매핑 파일 경로
# ──────────────────────────────────────────────────────────────────────
_ICD11_MAPPING_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "datasets", "official_icd11", "icd11_careflow_mapping.json",
)

# ──────────────────────────────────────────────────────────────────────
# Mock Data — 로컬 개발용 목 데이터
# In production: AlloyDB via MCP Toolbox / 프로덕션: MCP Toolbox → AlloyDB
# ──────────────────────────────────────────────────────────────────────

_MOCK_MEDICATIONS: dict[str, dict[str, Any]] = {
    "patient_001": {
        "current_medications": [
            {
                "name": "Metformin",
                "dosage": "1000mg",
                "frequency": "twice_daily",
                "prescribed_date": "2025-06-15",
                "condition": "Type 2 Diabetes",
            },
            {
                "name": "Amlodipine",
                "dosage": "5mg",
                "frequency": "once_daily",
                "prescribed_date": "2025-03-10",
                "condition": "Hypertension",
            },
        ],
        "recent_changes": [
            {
                "medication": "Metformin",
                "change_type": "dosage_increase",
                "from_dosage": "500mg",
                "to_dosage": "1000mg",
                "change_date": "2026-03-25",
                "reason": "insufficient glycemic control",
            },
        ],
    },
}

_MOCK_ADHERENCE: dict[str, list[dict[str, Any]]] = {
    "patient_001": [
        {"date": "2026-04-04", "medication": "Metformin", "taken": False, "scheduled_time": "08:00"},
        {"date": "2026-04-04", "medication": "Metformin", "taken": True, "scheduled_time": "20:00"},
        {"date": "2026-04-03", "medication": "Metformin", "taken": True, "scheduled_time": "08:00"},
        {"date": "2026-04-03", "medication": "Metformin", "taken": False, "scheduled_time": "20:00"},
        {"date": "2026-04-02", "medication": "Metformin", "taken": True, "scheduled_time": "08:00"},
        {"date": "2026-04-02", "medication": "Metformin", "taken": True, "scheduled_time": "20:00"},
        {"date": "2026-04-04", "medication": "Amlodipine", "taken": True, "scheduled_time": "09:00"},
        {"date": "2026-04-03", "medication": "Amlodipine", "taken": True, "scheduled_time": "09:00"},
        {"date": "2026-04-02", "medication": "Amlodipine", "taken": True, "scheduled_time": "09:00"},
    ],
}

_MOCK_HEALTH_METRICS: dict[str, dict[str, Any]] = {
    "patient_001": {
        "blood_glucose": {
            "latest_value": 142,
            "unit": "mg/dL",
            "measured_at": "2026-04-04T07:30:00",
            "trend": "rising",  # 상승 추세 / rising trend
            "last_7_days_avg": 135,
        },
        "blood_pressure": {
            "systolic": 148,
            "diastolic": 92,
            "unit": "mmHg",
            "measured_at": "2026-04-04T08:00:00",
            "trend": "stable",
        },
        "heart_rate": {
            "latest_value": 78,
            "unit": "bpm",
            "measured_at": "2026-04-04T08:00:00",
            "trend": "stable",
        },
        "weight": {
            "latest_value": 72.5,
            "unit": "kg",
            "measured_at": "2026-04-01T07:00:00",
            "trend": "stable",
        },
    },
}


# ──────────────────────────────────────────────────────────────────────
# Tool 1: get_patient_medications
# 환자의 현재 약물 + 최근 변경 사항 조회
# Retrieves current medications and recent prescription changes.
# ──────────────────────────────────────────────────────────────────────

def get_patient_medications(patient_id: str, tool_context: ToolContext) -> dict:
    """Get current medications and recent prescription changes for a patient.

    환자의 현재 복용 약물 목록과 최근 처방 변경 사항을 반환합니다.
    Symptom-medication correlation 분석의 핵심 데이터 소스입니다.

    Args:
        patient_id: The unique patient identifier (e.g., "patient_001").

    Returns:
        A dict containing current_medications list and recent_changes list.
    """
    # ---------------------------------------------------------------
    # 1단계: AlloyDB 우선 조회 / Step 1: Try AlloyDB first
    # 현재 약물 + 최근 처방 변경 사항을 두 쿼리로 조회
    # Fetch current medications and recent changes via two queries.
    # ---------------------------------------------------------------
    # 실제 스키마: medications(id, name, dosage, frequency, timing, status, prescribed_date, ...)
    # `condition` 컬럼은 스키마에 없으므로 제거
    # Actual schema: medications(...); no `condition` column — dropped.
    current_rows = query_dict(
        """
        SELECT id, name, dosage, frequency, timing, status, prescribed_date
        FROM medications
        WHERE patient_id = :pid
        ORDER BY prescribed_date DESC
        """,
        {"pid": patient_id},
    )
    if current_rows:
        # 날짜 직렬화 / Serialize date fields
        for row in current_rows:
            if hasattr(row.get("prescribed_date"), "strftime"):
                row["prescribed_date"] = row["prescribed_date"].strftime("%Y-%m-%d")

        # medication_changes 실제 스키마:
        #   (medication_id, patient_id, change_type, previous_dosage, new_dosage, reason, changed_at)
        # Actual schema of medication_changes uses previous_dosage/new_dosage/changed_at.
        change_rows = query_dict(
            """
            SELECT mc.medication_id, m.name AS medication, mc.change_type,
                   mc.previous_dosage AS from_dosage,
                   mc.new_dosage AS to_dosage,
                   mc.changed_at AS change_date,
                   mc.reason
            FROM medication_changes mc
            LEFT JOIN medications m ON m.id = mc.medication_id
            WHERE mc.patient_id = :pid
              AND mc.changed_at >= NOW() - INTERVAL '90 days'
            ORDER BY mc.changed_at DESC
            """,
            {"pid": patient_id},
        )
        # 날짜 직렬화 / Serialize change_date
        for row in change_rows:
            if hasattr(row.get("change_date"), "strftime"):
                row["change_date"] = row["change_date"].strftime("%Y-%m-%d")

        db_data = {
            "current_medications": current_rows,
            "recent_changes": change_rows,
        }
        logger.info(
            f"symptom.get_patient_medications.from_db: "
            f"{len(current_rows)} meds, {len(change_rows)} changes"
        )
        tool_context.state["patient_medications"] = db_data
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            **db_data,
        }

    # ---------------------------------------------------------------
    # 2단계: mock 데이터 fallback / Step 2: Fallback to mock data
    # ---------------------------------------------------------------
    logger.info("symptom.get_patient_medications.fallback_to_mock")
    data = _MOCK_MEDICATIONS.get(patient_id)
    if data is None:
        return {
            "status": "error",
            "message": f"No medication data found for patient: {patient_id}",
        }

    tool_context.state["patient_medications"] = data
    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        **data,
    }


# ──────────────────────────────────────────────────────────────────────
# Tool 2: get_adherence_history
# 복약 순응도 이력 조회
# Retrieves medication adherence history for the specified period.
#
# Safe Default Rule 5 연관:
#   NON-ADHERENCE + SYMPTOMS → 2회 이상 미복약 시 긴급도 자동 상향
#   If missed >= 2 doses AND symptoms present → auto-upgrade urgency
# ──────────────────────────────────────────────────────────────────────

def get_adherence_history(patient_id: str, days: int, tool_context: ToolContext) -> dict:
    """Get medication adherence history for a patient over the specified number of days.

    지정된 기간 동안의 복약 순응도 이력을 반환합니다.
    missed_doses 수치는 Safe Default Rule 5 판단에 직접 사용됩니다.

    Args:
        patient_id: The unique patient identifier (e.g., "patient_001").
        days: Number of days to look back for adherence history.

    Returns:
        A dict containing adherence records, total doses, missed count, and adherence rate.
    """
    # ---------------------------------------------------------------
    # 참고: AlloyDB 스키마에는 medication_adherence 테이블이 없으므로
    #      mock 데이터만 사용합니다.
    # Note: AlloyDB schema has no `medication_adherence` table; serve
    #       from the mock fallback only.
    # ---------------------------------------------------------------
    logger.info("symptom.adherence.mock_only")
    records = _MOCK_ADHERENCE.get(patient_id)
    if records is None:
        return {
            "status": "error",
            "message": f"No adherence data found for patient: {patient_id}",
        }

    # 지정된 기간 내 기록만 필터링 / Filter records within the requested window
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = [r for r in records if r["date"] >= cutoff_date]
    source = "mock"

    total_doses = len(filtered)
    missed_doses = sum(1 for r in filtered if not r["taken"])
    adherence_rate = ((total_doses - missed_doses) / total_doses * 100) if total_doses > 0 else 0.0

    result = {
        "status": "success",
        "source": source,
        "patient_id": patient_id,
        "period_days": days,
        "records": filtered,
        "summary": {
            "total_scheduled_doses": total_doses,
            "missed_doses": missed_doses,
            "adherence_rate_percent": round(adherence_rate, 1),
        },
    }

    # ⚠️ Safe Default Rule 5 참고 데이터를 상태에 저장
    # ⚠️ Persist missed-dose count for Safe Default Rule 5 evaluation
    tool_context.state["adherence_summary"] = result["summary"]
    return result


# ──────────────────────────────────────────────────────────────────────
# Tool 3: get_recent_health_metrics
# 최근 건강 지표 조회 (혈당, 혈압, 심박수, 체중 등)
# Retrieves latest health metrics for context-aware symptom analysis.
# ──────────────────────────────────────────────────────────────────────

def get_recent_health_metrics(patient_id: str, tool_context: ToolContext) -> dict:
    """Get recent health metrics (blood glucose, blood pressure, heart rate, weight) for a patient.

    최근 건강 지표를 반환합니다. 증상과 수치 이상 간의 상관관계 분석에 사용됩니다.
    예: 혈당 < 54mg/dL 또는 > 400mg/dL → HIGH 자동 분류.

    Args:
        patient_id: The unique patient identifier (e.g., "patient_001").

    Returns:
        A dict containing latest health metric values and trends.
    """
    # ---------------------------------------------------------------
    # 1단계: AlloyDB 우선 조회 / Step 1: Try AlloyDB first
    # 실제 스키마에 trend 컬럼이 없으므로, 최신값과 7일 평균을 각각
    # 단순 쿼리 2개로 조회한 뒤 병합합니다.
    # The real schema has no `trend` column — fetch latest values and
    # 7-day averages via two simple queries and merge the results.
    # ---------------------------------------------------------------
    latest_rows = query_dict(
        """
        SELECT DISTINCT ON (metric_type)
            metric_type, value_primary, value_secondary, unit, measured_at
        FROM health_metrics
        WHERE patient_id = :pid
        ORDER BY metric_type, measured_at DESC
        """,
        {"pid": patient_id},
    )
    if latest_rows:
        # 7일 평균은 별도 쿼리로 / Fetch 7-day averages as a separate query
        avg_rows = query_dict(
            """
            SELECT metric_type, AVG(value_primary) AS avg_7d
            FROM health_metrics
            WHERE patient_id = :pid
              AND measured_at >= NOW() - INTERVAL '7 days'
            GROUP BY metric_type
            """,
            {"pid": patient_id},
        )
        avg_map = {
            r["metric_type"]: r.get("avg_7d") for r in (avg_rows or [])
        }

        logger.info(f"symptom.health_metrics.from_db: {len(latest_rows)} metrics")
        metrics: dict[str, Any] = {}
        for row in latest_rows:
            mtype = row["metric_type"]
            measured_at = row.get("measured_at")
            if hasattr(measured_at, "isoformat"):
                measured_at = measured_at.isoformat()
            entry = {
                "latest_value": row.get("value_primary"),
                "unit": row.get("unit"),
                "measured_at": measured_at,
                # trend 컬럼이 스키마에 없음 — 기본값 "unknown"
                # No `trend` column in schema — default to "unknown".
                "trend": "unknown",
            }
            if avg_map.get(mtype) is not None:
                entry["last_7_days_avg"] = round(float(avg_map[mtype]), 1)
            # blood_pressure는 systolic/diastolic 분리 표현
            # For blood pressure, expose systolic/diastolic explicitly.
            if mtype == "blood_pressure":
                entry["systolic"] = row.get("value_primary")
                entry["diastolic"] = row.get("value_secondary")
            metrics[mtype] = entry

        tool_context.state["health_metrics"] = metrics
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "metrics": metrics,
        }

    # ---------------------------------------------------------------
    # 2단계: mock 데이터 fallback / Step 2: Fallback to mock data
    # ---------------------------------------------------------------
    logger.info("symptom.health_metrics.fallback_to_mock")
    metrics = _MOCK_HEALTH_METRICS.get(patient_id)
    if metrics is None:
        return {
            "status": "error",
            "message": f"No health metrics found for patient: {patient_id}",
        }

    tool_context.state["health_metrics"] = metrics
    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "metrics": metrics,
    }


# ──────────────────────────────────────────────────────────────────────
# Tool 4: lookup_icd11_code
# ICD-11 코드 매핑 조회
# Maps a symptom keyword to its WHO ICD-11 code.
# 출력 JSON의 icd11_codes 필드에 포함되어 EHR 연동에 활용됩니다.
# Used in output JSON's icd11_codes field for EHR system interoperability.
# ──────────────────────────────────────────────────────────────────────

# 인메모리 캐시 — 파일 I/O를 최소화
# In-memory cache to minimise file I/O
_icd11_cache: dict[str, dict[str, str]] | None = None


def _load_icd11_mapping() -> dict[str, dict[str, str]]:
    """Load ICD-11 mapping from the official dataset JSON file, with in-memory caching."""
    global _icd11_cache
    if _icd11_cache is not None:
        return _icd11_cache

    resolved = os.path.normpath(_ICD11_MAPPING_PATH)
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            _icd11_cache = json.load(f)
    except FileNotFoundError:
        # 파일이 없을 경우 빈 fallback 반환 — 프로덕션에서는 MCP로 대체
        # Fallback to empty if file not found; production uses MCP Toolbox
        _icd11_cache = {}
    return _icd11_cache


def _query_icd11_api(symptom: str) -> dict[str, Any] | None:
    """WHO ICD-11 Coding Tool API를 호출하여 증상 코드를 검색합니다.
    Query the WHO ICD-11 Coding Tool API for a symptom code.

    WHO ICD-11 API는 토큰 인증이 필요하지만, Coding Tool 검색은 공개 접근 가능.
    The WHO ICD-11 API requires token auth, but the Coding Tool search is publicly accessible.

    Args:
        symptom: 증상 키워드 (영문) / Symptom keyword in English.

    Returns:
        dict with ICD-11 code and title on success, None on failure.
        성공 시 ICD-11 코드/제목, 실패 시 None.
    """
    try:
        # ICD-11 Coding Tool 검색 API (공개 접근 가능)
        # ICD-11 Coding Tool search API (publicly accessible)
        query = symptom.strip().replace("_", " ")
        params = urllib.parse.urlencode({
            "q": query,
            "useFlexisearch": "true",
            "flatResults": "true",
        })
        url = f"https://icd.who.int/ct11/icd11/mms/search?{params}"

        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "API-Version": "v2",
            "Accept-Language": "en",
        })

        with urllib.request.urlopen(req, timeout=_API_TIMEOUT, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        entities = data.get("destinationEntities", [])
        if not entities:
            return None

        # 첫 번째 결과 사용 / Use first result
        best = entities[0]
        code = best.get("theCode", "")
        title = best.get("title", "")

        # HTML 태그 제거 (API 응답에 <em> 태그 포함 가능)
        # Strip HTML tags (API response may contain <em> tags)
        import re
        title_clean = re.sub(r"<[^>]+>", "", title) if title else ""

        if code and title_clean:
            return {
                "icd11_code": code,
                "icd11_title": title_clean,
                "api_source": True,
            }
        return None

    except Exception:
        # API 실패 시 None → 로컬 매핑 fallback 또는 not_found
        # On API failure → local mapping fallback or not_found
        return None


def lookup_icd11_code(symptom: str, tool_context: ToolContext) -> dict:
    """Look up the WHO ICD-11 code for a given symptom keyword.

    증상 키워드를 WHO ICD-11 코드로 매핑합니다.
    1차: 로컬 JSON 매핑 파일 참조 (빠르고 검증된 데이터)
    2차: 매핑에 없으면 WHO ICD-11 Coding Tool API로 fallback

    First: local JSON mapping (fast, curated data).
    Second: if not in mapping, fallback to WHO ICD-11 Coding Tool API.

    Args:
        symptom: A symptom keyword to look up (e.g., "dizziness", "chest_pain", "nausea").

    Returns:
        A dict with the ICD-11 code and title, or a not-found message.
    """
    mapping = _load_icd11_mapping()

    # 정규화: 소문자 + 공백→언더스코어 / Normalise: lowercase, space→underscore
    key = symptom.strip().lower().replace(" ", "_")

    # 1단계: 로컬 매핑에서 검색 (검증된 데이터, 빠름)
    # Step 1: Look up in local mapping (curated, fast)
    entry = mapping.get(key)
    if entry is not None:
        return {
            "status": "success",
            "symptom": symptom,
            "icd11_code": entry["code"],
            "icd11_title": entry["title"],
        }

    # 2단계: 로컬에 없으면 WHO ICD-11 API fallback
    # Step 2: If not in local mapping, fallback to WHO ICD-11 API
    api_result = _query_icd11_api(symptom)
    if api_result is not None:
        return {
            "status": "success",
            "symptom": symptom,
            "icd11_code": api_result["icd11_code"],
            "icd11_title": api_result["icd11_title"],
            "source": "WHO ICD-11 Coding Tool API",
        }

    # 3단계: 어디에서도 못 찾음 / Step 3: Not found anywhere
    return {
        "status": "not_found",
        "symptom": symptom,
        "message": (
            f"No ICD-11 mapping found for '{symptom}' in local cache or WHO ICD-11 API. "
            "Consider using a standardized symptom keyword."
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# Tool 5: send_escalation_alert
# 에스컬레이션 알림 전송
# Sends escalation alerts to caregivers and/or doctors.
#
# ⚠️ 안전 관련 핵심 도구 / Safety-critical tool
# HIGH urgency에서는 notify_caregiver=True, notify_doctor=True가 필수입니다.
# For HIGH urgency: both notify_caregiver and notify_doctor MUST be True.
# 프로덕션에서는 Gmail MCP를 통해 실제 이메일이 발송됩니다.
# In production: actual emails sent via Gmail MCP.
# ──────────────────────────────────────────────────────────────────────

def send_escalation_alert(
    patient_id: str,
    urgency: str,
    message: str,
    notify_caregiver: bool,
    notify_doctor: bool,
    tool_context: ToolContext,
) -> dict:
    """Send an escalation alert to caregiver and/or doctor based on urgency level.

    긴급도 수준에 따라 보호자 및/또는 의사에게 에스컬레이션 알림을 전송합니다.

    SAFETY RULES / 안전 규칙:
      - HIGH urgency → 보호자 + 의사 모두 알림 필수 (both must be notified)
      - MEDIUM urgency → 보호자 알림 필수 (caregiver must be notified)
      - LOW urgency → 알림 없음 (no alert needed, log only)

    Args:
        patient_id: The unique patient identifier.
        urgency: Urgency level — one of "LOW", "MEDIUM", "HIGH".
        message: The alert message describing the situation.
        notify_caregiver: Whether to notify the caregiver.
        notify_doctor: Whether to notify the doctor.

    Returns:
        A dict with alert status, timestamp, and notification details.
    """
    urgency_upper = urgency.strip().upper()

    # ──────────────────────────────────────────────────────────────
    # 안전 가드레일: HIGH일 때 반드시 의사에게도 알림
    # Safety guardrail: HIGH urgency MUST notify doctor
    # ──────────────────────────────────────────────────────────────
    if urgency_upper == "HIGH" and not notify_doctor:
        notify_doctor = True  # 강제 상향 / Force enable — safety override

    if urgency_upper == "HIGH" and not notify_caregiver:
        notify_caregiver = True  # 강제 상향 / Force enable — safety override

    # MEDIUM일 때 보호자 알림 강제
    # MEDIUM urgency must always notify caregiver
    if urgency_upper == "MEDIUM" and not notify_caregiver:
        notify_caregiver = True

    timestamp = datetime.now().isoformat()

    # Mock 알림 결과 / Mock alert result
    notifications_sent: list[str] = []
    if notify_caregiver:
        notifications_sent.append("caregiver (email: priya.sharma@example.com)")
    if notify_doctor:
        notifications_sent.append("doctor (email: dr.anand.mehta@example.com)")

    result = {
        "status": "success",
        "patient_id": patient_id,
        "urgency": urgency_upper,
        "message": message,
        "notifications_sent_to": notifications_sent,
        "timestamp": timestamp,
        # 프로덕션에서는 Gmail MCP message ID가 여기에 포함됩니다
        # In production: Gmail MCP message IDs would be included here
        "mock": True,
    }

    # 에스컬레이션 이력을 상태에 저장 / Persist escalation history to state
    if "escalation_log" not in tool_context.state:
        tool_context.state["escalation_log"] = []
    tool_context.state["escalation_log"] = tool_context.state["escalation_log"] + [result]

    return result
