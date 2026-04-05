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

from datetime import datetime
from typing import Optional

from google.adk.tools import ToolContext
from careflow.db.alloydb_client import query_dict, execute_write
import json


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
        "email": "priya.sharma@example.com",
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
    sql = """INSERT INTO visit_records (patient_id, visit_date, structured_summary, doctor_name, hospital_name, key_findings, raw_input)
             VALUES (:pid, :vdate, :summ, :doc, :hosp, COALESCE(:kf::jsonb, '{}'::jsonb), :raw)
             RETURNING id"""
    db_rows = execute_write(sql, {
        "pid": patient_id, "vdate": visit_date, "summ": summary,
        "doc": doctor_name or "Unknown", "hosp": hospital_name or "Unknown",
        "kf": key_findings, "raw": summary
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


def search_medical_history(
    patient_id: str,
    query: str,
    tool_context: ToolContext,
    top_k: int = 5,
) -> dict:
    """Search patient's visit records using keyword matching.

    In production this generates a vector embedding and uses pgvector
    for cosine similarity search. Here we use keyword matching as a proxy.

    환자의 방문 기록을 키워드 매칭으로 검색합니다.

    Args:
        patient_id: Unique patient identifier.
        query: Natural language search query.
        tool_context: ADK ToolContext for state management.
        top_k: Number of results to return (default 5).

    Returns:
        dict with "status", "query", "results_count", and "results" list.
    """
    # 검색 이력 기록 / Log search history
    search_log = tool_context.state.get("search_log", [])
    search_log.append({
        "query": query,
        "searched_at": datetime.now().isoformat(),
    })
    tool_context.state["search_log"] = search_log

    sql = """SELECT id as visit_id, visit_date, doctor_name, hospital_name, structured_summary as summary
             FROM visit_records
             WHERE patient_id = :pid AND (structured_summary ILIKE :q OR key_findings::text ILIKE :q)
             ORDER BY visit_date DESC
             LIMIT :lim"""
    db_rows = query_dict(sql, {"pid": patient_id, "q": f"%{query}%", "lim": top_k})
    if db_rows:
        for tuple_row in db_rows:
            tuple_row["visit_id"] = str(tuple_row["visit_id"])
            if hasattr(tuple_row["visit_date"], "isoformat"):
                tuple_row["visit_date"] = tuple_row["visit_date"].isoformat()
        return {
            "status": "success",
            "source": "alloydb",
            "query": query,
            "results_count": len(db_rows),
            "results": db_rows,
        }

    records = _get_visit_records_from_state(tool_context)

    # 해당 환자의 레코드만 필터 / Filter records for this patient
    patient_records = [r for r in records if r.get("patient_id") == patient_id]

    # 키워드 매칭으로 유사도 계산 / Calculate similarity via keyword matching
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

    # 점수순 정렬 + top_k 제한 / Sort by score + limit
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    results = scored[:top_k]

    return {
        "status": "success",
        "source": "mock",
        "query": query,
        "results_count": len(results),
        "results": results,
    }


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
