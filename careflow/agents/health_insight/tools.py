# ============================================================================
# CareFlow Health Insight Agent - Function Tools
# 건강 인사이트 에이전트 도구 함수 정의
# ============================================================================
# Mock 데이터 기반으로 동작하는 FunctionTool 모음.
# 실제 프로덕션에서는 MCP Toolbox for Databases → AlloyDB로 교체 예정.
#
# Tools backed by mock data for development/demo.
# In production, these will be replaced by MCP Toolbox → AlloyDB connections.
# ============================================================================

import logging
from datetime import datetime, timedelta
from typing import Optional

from google.adk.tools import ToolContext

# AlloyDB 우선 조회용 공용 헬퍼 / Shared helper for AlloyDB-first lookups
from careflow.db.alloydb_client import query_dict
from careflow.agents.shared.patient_utils import resolve_patient_id as _resolve_patient_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock Data Store
# 실제 DB 없이 동작하도록 하드코딩된 테스트 데이터
# Hardcoded test data to operate without a real database
# ---------------------------------------------------------------------------

_MOCK_HEALTH_METRICS = {
    "patient_001": {
        "blood_pressure_systolic": [
            {"date": "2026-01-05", "value": 130},
            {"date": "2026-01-20", "value": 132},
            {"date": "2026-02-05", "value": 135},
            {"date": "2026-02-20", "value": 136},
            {"date": "2026-03-05", "value": 138},
            {"date": "2026-03-20", "value": 140},
        ],
        "blood_pressure_diastolic": [
            {"date": "2026-01-05", "value": 82},
            {"date": "2026-01-20", "value": 84},
            {"date": "2026-02-05", "value": 85},
            {"date": "2026-02-20", "value": 86},
            {"date": "2026-03-05", "value": 88},
            {"date": "2026-03-20", "value": 90},
        ],
        "fasting_blood_glucose": [
            {"date": "2026-01-05", "value": 145},
            {"date": "2026-01-20", "value": 142},
            {"date": "2026-02-05", "value": 138},
            {"date": "2026-02-20", "value": 132},
            {"date": "2026-03-05", "value": 130},
            {"date": "2026-03-20", "value": 128},
        ],
        "weight_kg": [
            {"date": "2026-01-05", "value": 78.2},
            {"date": "2026-02-05", "value": 78.0},
            {"date": "2026-03-05", "value": 78.1},
            {"date": "2026-03-20", "value": 78.0},
        ],
        "heart_rate": [
            {"date": "2026-01-05", "value": 72},
            {"date": "2026-02-05", "value": 74},
            {"date": "2026-03-05", "value": 73},
            {"date": "2026-03-20", "value": 71},
        ],
    }
}

_MOCK_MEDICATIONS = {
    "patient_001": [
        {
            "medication": "Metformin",
            "dosage": "1000mg",
            "frequency": "2x/day",
            "start_date": "2025-12-01",
            "previous_dosage": "500mg",
            "dosage_change_date": "2025-12-01",
            "adherence_pct": 92,
        },
        {
            "medication": "Amlodipine",
            "dosage": "5mg",
            "frequency": "1x/day",
            "start_date": "2025-06-15",
            "previous_dosage": None,
            "dosage_change_date": None,
            "adherence_pct": 88,
        },
    ]
}

_MOCK_VISIT_RECORDS = {
    "patient_001": [
        {
            "date": "2026-01-10",
            "provider": "Dr. Patel",
            "type": "routine_checkup",
            "notes": "DM2+HTN stable. Metformin increased to 1000mg. Continue Amlodipine 5mg.",
            "next_visit": "2026-04-10",
        },
        {
            "date": "2025-10-15",
            "provider": "Dr. Patel",
            "type": "routine_checkup",
            "notes": "Fasting glucose elevated. Consider Metformin dosage increase.",
            "next_visit": "2026-01-10",
        },
        {
            "date": "2025-07-12",
            "provider": "Dr. Patel",
            "type": "routine_checkup",
            "notes": "BP well controlled. DM2 management adequate with current regimen.",
            "next_visit": "2025-10-15",
        },
    ]
}


# ---------------------------------------------------------------------------
# Tool Functions
# 에이전트가 호출할 수 있는 도구 함수들
# Functions callable by the LLM agent via function-calling
# ---------------------------------------------------------------------------


def get_health_metrics(
    patient_id: str,
    metric_type: str,
    days: int,
    tool_context: ToolContext,
) -> dict:
    """Retrieve health metrics for a patient over a specified period.

    Queries time-series health data (blood pressure, blood glucose, weight, etc.)
    from the patient's records. In production this reads from AlloyDB via MCP Toolbox.

    환자의 건강 지표를 지정된 기간 동안 조회합니다.
    혈압, 혈당, 체중 등 시계열 건강 데이터를 반환합니다.

    Args:
        patient_id: Unique patient identifier (e.g. "patient_001").
        metric_type: Type of metric to retrieve. One of:
            blood_pressure_systolic, blood_pressure_diastolic,
            fasting_blood_glucose, weight_kg, heart_rate.
        days: Number of past days to look back from today.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "metric_type", "period_days", "data_points",
        and "values" (list of {date, value}).
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    # DB의 metric_type은 "blood_pressure" (systolic+diastolic 통합), mock은 별도.
    # LLM이 "blood_pressure_systolic" / "blood_pressure_diastolic"로 보내는 경우 매핑.
    _METRIC_ALIAS = {
        "blood_pressure_systolic": "blood_pressure",
        "blood_pressure_diastolic": "blood_pressure",
        "bp_systolic": "blood_pressure",
        "bp_diastolic": "blood_pressure",
        "fasting_blood_glucose": "blood_glucose",
        "weight_kg": "weight",
    }
    db_metric_type = _METRIC_ALIAS.get(metric_type.lower(), metric_type)
    # state에 조회 이력 기록 / Log query history in session state
    query_log = tool_context.state.get("health_metric_queries", [])
    query_log.append({
        "patient_id": patient_id,
        "metric_type": metric_type,
        "days": days,
        "queried_at": datetime.now().isoformat(),
    })
    tool_context.state["health_metric_queries"] = query_log

    # ---------------------------------------------------------------
    # 1단계: AlloyDB 우선 조회 / Step 1: Try AlloyDB first
    # 환경변수 ALLOYDB_CONN_URI가 설정되어 있으면 실 DB에서 시계열을 가져온다.
    # If ALLOYDB_CONN_URI is set, fetch the time-series from AlloyDB.
    # ---------------------------------------------------------------
    db_rows = query_dict(
        """
        SELECT measured_at, value_primary, value_secondary, unit
        FROM health_metrics
        WHERE patient_id = :pid
          AND metric_type = :mtype
          AND measured_at >= NOW() - (:days || ' days')::interval
        ORDER BY measured_at ASC
        """,
        {"pid": patient_id, "mtype": db_metric_type, "days": days},
    )
    if db_rows:
        logger.info(f"health_metrics.from_db: {len(db_rows)} rows")
        # blood_pressure는 value_primary=systolic, value_secondary=diastolic.
        # 원래 metric_type에 맞춰 필드명을 분기.
        is_bp = db_metric_type == "blood_pressure"
        values = []
        for row in db_rows:
            date_str = (
                row["measured_at"].strftime("%Y-%m-%d")
                if hasattr(row["measured_at"], "strftime")
                else str(row["measured_at"])
            )
            entry = {"date": date_str}
            if is_bp:
                entry["systolic"] = row.get("value_primary")
                entry["diastolic"] = row.get("value_secondary")
                entry["value"] = f"{row.get('value_primary')}/{row.get('value_secondary')}"
            else:
                entry["value"] = row.get("value_primary")
            entry["unit"] = row.get("unit", "")
            values.append(entry)
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "metric_type": metric_type,
            "period_days": days,
            "data_points": len(values),
            "values": values,
        }

    # ---------------------------------------------------------------
    # 2단계: mock 데이터 fallback / Step 2: Fallback to mock data
    # ---------------------------------------------------------------
    logger.info("health_metrics.fallback_to_mock")
    patient_data = _MOCK_HEALTH_METRICS.get(patient_id)
    if patient_data is None:
        return {
            "status": "error",
            "message": f"No data found for patient '{patient_id}'.",
        }

    metric_data = patient_data.get(metric_type)
    if metric_data is None:
        return {
            "status": "error",
            "message": (
                f"Unknown metric_type '{metric_type}' for patient '{patient_id}'. "
                f"Available: {list(patient_data.keys())}"
            ),
        }

    # 기간 필터 / Filter by date range
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = [entry for entry in metric_data if entry["date"] >= cutoff]

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "metric_type": metric_type,
        "period_days": days,
        "data_points": len(filtered),
        "values": filtered,
    }


def get_medication_history(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve full medication history for a patient.

    Returns current medications, dosage change history, and adherence percentages.
    In production this reads from AlloyDB via MCP Toolbox.

    환자의 전체 약물 이력을 조회합니다.
    현재 복용 약물, 용량 변경 이력, 복약 순응도를 반환합니다.

    Args:
        patient_id: Unique patient identifier (e.g. "patient_001").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "medication_count", and "medications" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    # state에 최근 조회 환자 기록 / Track last queried patient in state
    tool_context.state["last_medication_query_patient"] = patient_id

    # ---------------------------------------------------------------
    # 1단계: AlloyDB 우선 조회 / Step 1: Try AlloyDB first
    # ---------------------------------------------------------------
    # medications 테이블에서 기본 약물 정보 조회
    # Fetch base medication info from the `medications` table.
    db_rows = query_dict(
        """
        SELECT id, name, dosage, frequency, timing, status, prescribed_date
        FROM medications
        WHERE patient_id = :pid
        ORDER BY prescribed_date DESC
        """,
        {"pid": patient_id},
    )
    if db_rows:
        logger.info(f"medication_history.from_db: {len(db_rows)} rows")
        # 날짜 직렬화 + 표준 필드 매핑 / Serialize dates and normalize fields
        medications = []
        for row in db_rows:
            prescribed = row.get("prescribed_date")
            if hasattr(prescribed, "strftime"):
                prescribed = prescribed.strftime("%Y-%m-%d")
            medications.append({
                "medication": row.get("name"),
                "dosage": row.get("dosage"),
                "frequency": row.get("frequency"),
                "timing": row.get("timing"),
                "status": row.get("status"),
                "start_date": prescribed,
            })
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "medication_count": len(medications),
            "medications": medications,
        }

    # ---------------------------------------------------------------
    # 2단계: mock 데이터 fallback / Step 2: Fallback to mock data
    # ---------------------------------------------------------------
    logger.info("medication_history.fallback_to_mock")
    medications = _MOCK_MEDICATIONS.get(patient_id)
    if medications is None:
        return {
            "status": "error",
            "message": f"No medication records found for patient '{patient_id}'.",
        }

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "medication_count": len(medications),
        "medications": medications,
    }


def get_visit_records(
    patient_id: str,
    days: int,
    tool_context: ToolContext,
) -> dict:
    """Retrieve visit records for a patient over a specified period.

    Returns past visit details including provider, type, notes, and next scheduled visit.
    In production this reads from AlloyDB via MCP Toolbox.

    환자의 방문 기록을 지정된 기간 동안 조회합니다.
    담당의, 방문 유형, 진료 노트, 다음 예약일 등을 반환합니다.

    Args:
        patient_id: Unique patient identifier (e.g. "patient_001").
        days: Number of past days to look back from today.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "period_days", "record_count", and "records" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    # ---------------------------------------------------------------
    # 1단계: AlloyDB 우선 조회 / Step 1: Try AlloyDB first
    # ---------------------------------------------------------------
    # 실제 schema 컬럼: visit_date, doctor_name, hospital_name, structured_summary, key_findings
    # Real schema columns: visit_date, doctor_name, hospital_name, structured_summary, key_findings
    db_rows = query_dict(
        """
        SELECT visit_date AS date,
               doctor_name AS provider,
               hospital_name AS hospital,
               structured_summary AS notes,
               key_findings
        FROM visit_records
        WHERE patient_id = :pid
          AND visit_date >= (CURRENT_DATE - (:days || ' days')::interval)
        ORDER BY visit_date DESC
        """,
        {"pid": patient_id, "days": days},
    )
    if db_rows:
        logger.info(f"visit_records.from_db: {len(db_rows)} rows")
        # 날짜 직렬화 + key_findings 는 이미 dict (JSONB) 이므로 그대로 전달
        # Serialize dates; key_findings is already a dict from JSONB
        for row in db_rows:
            if hasattr(row.get("date"), "strftime"):
                row["date"] = row["date"].strftime("%Y-%m-%d")

        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "period_days": days,
            "record_count": len(db_rows),
            "records": db_rows,
        }

    # ---------------------------------------------------------------
    # 2단계: mock 데이터 fallback / Step 2: Fallback to mock data
    # ---------------------------------------------------------------
    logger.info("visit_records.fallback_to_mock")
    records = _MOCK_VISIT_RECORDS.get(patient_id)
    if records is None:
        return {
            "status": "error",
            "message": f"No visit records found for patient '{patient_id}'.",
        }

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = [r for r in records if r["date"] >= cutoff]

    # state에 다음 방문일 저장 (pre-visit summary 생성 시 활용)
    # Store next visit date in state (used for pre-visit summary generation)
    if filtered:
        next_visits = [r.get("next_visit") for r in filtered if r.get("next_visit")]
        if next_visits:
            tool_context.state["upcoming_visit_date"] = max(next_visits)

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "period_days": days,
        "record_count": len(filtered),
        "records": filtered,
    }


def calculate_trend(
    values: list[float],
    tool_context: ToolContext,
) -> dict:
    """Calculate the trend direction and statistics for a time-series of numeric values.

    Uses simple linear regression slope to determine whether the series is
    rising, falling, or stable. Provides min, max, average, and data quality flags.

    숫자 시계열 데이터의 트렌드 방향과 통계를 계산합니다.
    단순 선형 회귀 기울기를 사용하여 상승/하락/안정 여부를 판별합니다.

    Args:
        values: List of numeric values in chronological order (oldest first).
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "trend" (rising/falling/stable), "slope",
        "data_points", "min", "max", "average", and optional "warning".
    """
    if not values or len(values) < 2:
        return {
            "status": "error",
            "message": "Insufficient data for trend analysis. Need at least 2 data points.",
        }

    n = len(values)
    avg_val = sum(values) / n

    # 단순 선형 회귀 기울기 계산 / Simple linear regression slope
    # slope = sum((xi - x_mean)(yi - y_mean)) / sum((xi - x_mean)^2)
    x_mean = (n - 1) / 2.0
    numerator = sum((i - x_mean) * (values[i] - avg_val) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0.0

    # 트렌드 분류 / Classify trend direction
    # threshold: 평균값의 1% 미만 변화는 안정으로 간주
    # threshold: changes less than 1% of mean are considered stable
    threshold = avg_val * 0.01
    if slope > threshold:
        trend = "rising"
    elif slope < -threshold:
        trend = "falling"
    else:
        trend = "stable"

    result = {
        "status": "success",
        "trend": trend,
        "slope": round(slope, 4),
        "data_points": n,
        "min": min(values),
        "max": max(values),
        "average": round(avg_val, 2),
    }

    # 데이터 품질 경고 / Data quality warnings
    if n < 3:
        result["warning"] = "Insufficient data for reliable trend analysis (< 3 points)."

    # state에 마지막 트렌드 결과 저장 / Cache last trend result in state
    tool_context.state["last_trend_result"] = result

    return result
