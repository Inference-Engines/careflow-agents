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

from datetime import datetime, timedelta
from typing import Optional

from google.adk.tools import ToolContext


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
    # state에 조회 이력 기록 / Log query history in session state
    query_log = tool_context.state.get("health_metric_queries", [])
    query_log.append({
        "patient_id": patient_id,
        "metric_type": metric_type,
        "days": days,
        "queried_at": datetime.now().isoformat(),
    })
    tool_context.state["health_metric_queries"] = query_log

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
    # state에 최근 조회 환자 기록 / Track last queried patient in state
    tool_context.state["last_medication_query_patient"] = patient_id

    medications = _MOCK_MEDICATIONS.get(patient_id)
    if medications is None:
        return {
            "status": "error",
            "message": f"No medication records found for patient '{patient_id}'.",
        }

    return {
        "status": "success",
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
