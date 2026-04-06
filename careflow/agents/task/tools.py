# ============================================================================
# CareFlow Task Agent — Function Tools
# 태스크 에이전트 도구 함수 정의
# ============================================================================
# Mock 데이터 기반으로 동작하는 FunctionTool 모음.
# 실제 프로덕션에서는 AlloyDB + MCP Toolbox로 교체 예정.
#
# Tools backed by mock data for development/demo.
# In production, these will be replaced by AlloyDB/Toolbox integration.
# ============================================================================

import logging
from datetime import datetime
from typing import Optional

from google.adk.tools import ToolContext
from careflow.db.alloydb_client import query_dict, execute_write, get_db_engine

logger = logging.getLogger(__name__)


def _is_db_available() -> bool:
    """Check whether AlloyDB engine is configured and reachable.

    ``query_dict`` returns ``[]`` for both "no engine" and "no rows". This
    helper lets tool functions distinguish the two and avoid silently falling
    back to mock when the DB is present but the query returned 0 rows.
    """
    return get_db_engine() is not None


from careflow.agents.shared.patient_utils import resolve_patient_id as _resolve_patient_id


# ---------------------------------------------------------------------------
# Mock Data Store
# 실제 AlloyDB 없이 동작하도록 하드코딩된 테스트 데이터
# Hardcoded test data to operate without a real AlloyDB connection
# ---------------------------------------------------------------------------

_MOCK_MEDICATIONS = [
    {
        "medication_id": "MED-001",
        "patient_id": "patient_001",
        "name": "Metformin",
        "dosage": "1000mg",
        "frequency": "twice_daily",
        "timing": "with_meals",
        "status": "active",
        "prescribed_date": "2025-12-01",
    },
    {
        "medication_id": "MED-002",
        "patient_id": "patient_001",
        "name": "Amlodipine",
        "dosage": "5mg",
        "frequency": "once_daily",
        "timing": "morning",
        "status": "active",
        "prescribed_date": "2025-11-15",
    },
    {
        "medication_id": "MED-003",
        "patient_id": "patient_001",
        "name": "Aspirin",
        "dosage": "75mg",
        "frequency": "once_daily",
        "timing": "after_breakfast",
        "status": "active",
        "prescribed_date": "2025-10-01",
    },
    {
        "medication_id": "MED-004",
        "patient_id": "patient_001",
        "name": "Atorvastatin",
        "dosage": "20mg",
        "frequency": "once_daily",
        "timing": "bedtime",
        "status": "active",
        "prescribed_date": "2025-11-15",
    },
    {
        "medication_id": "MED-005",
        "patient_id": "patient_001",
        "name": "Lisinopril",
        "dosage": "10mg",
        "frequency": "once_daily",
        "timing": "morning",
        "status": "active",
        "prescribed_date": "2026-01-10",
    },
]

# 오프라인 폴백 전용 상호작용 테이블 — RxNav API 장애 시에만 사용.
# 평상시에는 NIH RxNav(DrugBank)가 권위 있는 소스이며, 여기는 백업.
#
# OFFLINE FALLBACK ONLY. Used only when the RxNav API is unreachable.
# The authoritative source is NIH RxNav (DrugBank) via shared.rxnorm_api.
_KNOWN_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "HIGH",
        "concern": "Increased risk of gastrointestinal and intracranial bleeding",
        "recommendation": "Requires close INR monitoring. Consult prescribing physician before co-administration.",
    },
    ("metformin", "lisinopril"): {
        "severity": "LOW",
        "concern": "Possible increased hypoglycemia risk — generally safe but monitor blood glucose",
        "recommendation": "Continue with regular blood glucose monitoring.",
    },
    ("amlodipine", "atorvastatin"): {
        "severity": "MODERATE",
        "concern": "Amlodipine may increase Atorvastatin plasma levels, raising myopathy risk",
        "recommendation": "Keep Atorvastatin dose ≤ 20mg when combined with Amlodipine.",
    },
    ("warfarin", "metformin"): {
        "severity": "MODERATE",
        "concern": "Metformin may alter Warfarin metabolism; bleeding risk slightly increased",
        "recommendation": "Monitor INR closely when initiating or changing Metformin dose.",
    },
    ("lisinopril", "aspirin"): {
        "severity": "LOW",
        "concern": "High-dose Aspirin may reduce antihypertensive effect of Lisinopril",
        "recommendation": "Low-dose Aspirin (75-100mg) is generally safe. Monitor blood pressure.",
    },
}

# 약물 정보 참조 데이터 / Medication reference data
_MEDICATION_INFO = {
    "metformin": {
        "name": "Metformin",
        "class": "Biguanide",
        "uses": "Type 2 Diabetes — first-line oral antidiabetic",
        "common_dosage": "500-2000mg/day in divided doses",
        "side_effects": "GI upset, lactic acidosis (rare), B12 deficiency (long-term)",
        "contraindications": "Severe renal impairment (eGFR < 30), acute metabolic acidosis",
    },
    "amlodipine": {
        "name": "Amlodipine",
        "class": "Calcium Channel Blocker",
        "uses": "Hypertension, angina",
        "common_dosage": "5-10mg once daily",
        "side_effects": "Peripheral edema, dizziness, flushing",
        "contraindications": "Severe aortic stenosis, cardiogenic shock",
    },
    "aspirin": {
        "name": "Aspirin",
        "class": "Antiplatelet / NSAID",
        "uses": "Cardiovascular prophylaxis, pain relief",
        "common_dosage": "75-100mg daily (cardioprotective), 325-650mg (analgesic)",
        "side_effects": "GI bleeding, peptic ulcer, tinnitus",
        "contraindications": "Active peptic ulcer, bleeding disorders, aspirin allergy",
    },
    "warfarin": {
        "name": "Warfarin",
        "class": "Vitamin K Antagonist (Anticoagulant)",
        "uses": "Atrial fibrillation, DVT/PE prophylaxis, mechanical heart valves",
        "common_dosage": "2-10mg daily, adjusted by INR",
        "side_effects": "Bleeding, bruising, skin necrosis (rare)",
        "contraindications": "Active bleeding, pregnancy, severe liver disease",
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "class": "HMG-CoA Reductase Inhibitor (Statin)",
        "uses": "Hyperlipidemia, cardiovascular risk reduction",
        "common_dosage": "10-80mg once daily",
        "side_effects": "Myalgia, elevated liver enzymes, rhabdomyolysis (rare)",
        "contraindications": "Active liver disease, pregnancy",
    },
    "lisinopril": {
        "name": "Lisinopril",
        "class": "ACE Inhibitor",
        "uses": "Hypertension, heart failure, post-MI, diabetic nephropathy",
        "common_dosage": "10-40mg once daily",
        "side_effects": "Dry cough, hyperkalemia, angioedema (rare)",
        "contraindications": "History of angioedema with ACE inhibitors, pregnancy",
    },
}

import uuid as _uuid


# ---------------------------------------------------------------------------
# Helper Functions
# 내부 유틸리티 함수 / Internal utility functions
# ---------------------------------------------------------------------------

def _get_next_med_id() -> str:
    """UUID4 기반 고유 mock 약물 ID — global counter 제거 (thread-safe).
    Generate unique mock medication ID via UUID4 short suffix."""
    return f"MED-{_uuid.uuid4().hex[:8]}"


def _get_next_task_id() -> str:
    """UUID4 기반 고유 mock 태스크 ID — global counter 제거 (thread-safe).
    Generate unique mock task ID via UUID4 short suffix."""
    return f"TASK-{_uuid.uuid4().hex[:8]}"


def _get_medications_from_state(tool_context: ToolContext) -> list:
    """state에서 약물 목록 로드 (없으면 mock 데이터 초기화).

    Load medications from state (initialize with mock data if empty).
    """
    medications = tool_context.state.get("medications")
    if medications is None:
        medications = [med.copy() for med in _MOCK_MEDICATIONS]
        tool_context.state["medications"] = medications
    return medications


def _save_medications_to_state(tool_context: ToolContext, medications: list) -> None:
    """state에 약물 목록 저장 / Save medications list to state."""
    tool_context.state["medications"] = medications


# ---------------------------------------------------------------------------
# Tool Functions
# 에이전트가 호출할 수 있는 도구 함수들
# Functions callable by the LLM agent via function-calling
# ---------------------------------------------------------------------------


def get_current_medications(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve all current medications for a patient.

    Returns the full medication list with dosage, frequency, timing, and status.
    In production this queries AlloyDB via MCP Toolbox.

    환자의 현재 약물 전체 목록을 반환합니다.

    Args:
        patient_id: Unique patient identifier (e.g. "patient_001").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "medication_count", and "medications" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    # DB 가용 여부를 먼저 판정 — "DB 연결 실패"와 "결과 0건" 구분.
    # Distinguish "DB unavailable" from "DB returned 0 rows".
    if _is_db_available():
        sql = "SELECT * FROM medications WHERE patient_id = :pid AND status = 'active'"
        db_rows = query_dict(sql, {"pid": patient_id})
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "medication_count": len(db_rows),
            "medications": db_rows,
        }

    # AlloyDB 미설정 → mock fallback (로그에 source 명시).
    logger.info("get_current_medications: alloydb unavailable, using mock")
    medications = _get_medications_from_state(tool_context)

    patient_meds = [
        med for med in medications
        if med.get("patient_id") == patient_id
    ]

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "medication_count": len(patient_meds),
        "medications": patient_meds,
    }


def add_medication(
    patient_id: str,
    name: str,
    dosage: str,
    frequency: str,
    timing: str,
    tool_context: ToolContext,
    notes: Optional[str] = None,
) -> dict:
    """Add a new medication to the patient's record.

    Creates a new medication entry with active status and logs it.
    In production this inserts into AlloyDB via MCP Toolbox.

    환자의 약물 기록에 새 약물을 추가합니다.

    Args:
        patient_id: Unique patient identifier.
        name: Medication name (e.g. "Metformin").
        dosage: Dosage (e.g. "1000mg").
        frequency: Frequency (e.g. "twice_daily").
        timing: Timing (e.g. "with_meals").
        tool_context: ADK ToolContext for state management.
        notes: Optional additional notes.

    Returns:
        dict with "status", "medication_id", and created medication details.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    if _is_db_available():
        sql = """INSERT INTO medications (patient_id, name, dosage, frequency, timing, status, prescribed_date, notes)
                 VALUES (:pid, :name, :dos, :freq, :tim, 'active', CURRENT_DATE, :notes)
                 RETURNING id"""
        db_rows = execute_write(sql, {
            "pid": patient_id, "name": name, "dos": dosage,
            "freq": frequency, "tim": timing, "notes": notes or ""
        })
        if db_rows:
            return {
                "status": "success",
                "source": "alloydb",
                "medication_id": str(db_rows[0]["id"]),
                "name": name,
                "dosage": dosage,
                "frequency": frequency,
                "timing": timing,
                "message": f"Medication '{name} {dosage}' added successfully.",
            }
        return {
            "status": "error",
            "source": "alloydb",
            "message": f"Failed to insert medication '{name}' into AlloyDB.",
        }

    logger.info("add_medication: alloydb unavailable, using mock")
    medications = _get_medications_from_state(tool_context)

    med_id = _get_next_med_id()
    new_med = {
        "medication_id": med_id,
        "patient_id": patient_id,
        "name": name,
        "dosage": dosage,
        "frequency": frequency,
        "timing": timing,
        "status": "active",
        "prescribed_date": datetime.now().strftime("%Y-%m-%d"),
        "notes": notes or "",
    }
    medications.append(new_med)
    _save_medications_to_state(tool_context, medications)

    return {
        "status": "success",
        "source": "mock",
        "medication_id": med_id,
        "name": name,
        "dosage": dosage,
        "frequency": frequency,
        "timing": timing,
        "message": f"Medication '{name} {dosage}' added successfully.",
    }


def update_medication_status(
    medication_id: str,
    new_status: str,
    tool_context: ToolContext,
    new_dosage: Optional[str] = None,
    new_frequency: Optional[str] = None,
    new_timing: Optional[str] = None,
) -> dict:
    """Update an existing medication's status, dosage, frequency, or timing.

    기존 약물의 상태, 용량, 빈도, 복용 시점을 업데이트합니다.

    Args:
        medication_id: The medication ID to update (e.g. "MED-001").
        new_status: New status — "active", "modified", or "discontinued".
        tool_context: ADK ToolContext for state management.
        new_dosage: Updated dosage, or None to keep existing.
        new_frequency: Updated frequency, or None to keep existing.
        new_timing: Updated timing, or None to keep existing.

    Returns:
        dict with "status", updated medication details, and "message".
    """
    if _is_db_available():
        sql = """UPDATE medications
                 SET status = :status,
                     dosage = COALESCE(:dosage, dosage),
                     frequency = COALESCE(:frequency, frequency),
                     timing = COALESCE(:timing, timing),
                     updated_at = NOW()
                 WHERE id = :mid
                 RETURNING id, name, dosage, frequency, timing, status"""
        db_rows = execute_write(sql, {
            "status": new_status, "dosage": new_dosage,
            "frequency": new_frequency, "timing": new_timing,
            "mid": medication_id
        })
        if db_rows:
            row = db_rows[0]
            return {
                "status": "success",
                "source": "alloydb",
                "medication_id": str(row["id"]),
                "previous": "unknown (db updated)",
                "updated": {
                    "dosage": row.get("dosage"), "frequency": row.get("frequency"),
                    "timing": row.get("timing"), "status": row.get("status")
                },
                "message": f"Medication '{row.get('name')}' updated to {new_status}."
            }
        return {
            "status": "error",
            "source": "alloydb",
            "message": f"Medication '{medication_id}' not found in AlloyDB.",
        }

    logger.info("update_medication: alloydb unavailable, using mock")
    medications = _get_medications_from_state(tool_context)

    target = None
    for med in medications:
        if med["medication_id"] == medication_id:
            target = med
            break

    if target is None:
        return {
            "status": "error",
            "message": f"Medication '{medication_id}' not found.",
        }

    # 이전 값 보존 / Preserve previous values
    previous = {
        "dosage": target["dosage"],
        "frequency": target["frequency"],
        "timing": target["timing"],
        "status": target["status"],
    }

    target["status"] = new_status
    if new_dosage:
        target["dosage"] = new_dosage
    if new_frequency:
        target["frequency"] = new_frequency
    if new_timing:
        target["timing"] = new_timing

    _save_medications_to_state(tool_context, medications)

    return {
        "status": "success",
        "source": "mock",
        "medication_id": medication_id,
        "previous": previous,
        "updated": {
            "dosage": target["dosage"],
            "frequency": target["frequency"],
            "timing": target["timing"],
            "status": target["status"],
        },
        "message": f"Medication '{target['name']}' updated to {new_status}.",
    }


def log_medication_change(
    medication_id: str,
    change_type: str,
    tool_context: ToolContext,
    previous_dosage: Optional[str] = None,
    new_dosage: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """Log a medication change event for audit tracking.

    약물 변경 이벤트를 감사 추적용으로 기록합니다.

    Args:
        medication_id: The medication ID that was changed.
        change_type: Type of change — "new", "dosage_change", or "discontinued".
        tool_context: ADK ToolContext for state management.
        previous_dosage: Previous dosage value (for changes).
        new_dosage: New dosage value (for changes).
        reason: Reason for the change.

    Returns:
        dict with "status" and change log details.
    """
    if _is_db_available():
        sql = """INSERT INTO medication_changes
                 (medication_id, patient_id, change_type, previous_dosage, new_dosage, reason, changed_by)
                 VALUES (:mid, (SELECT patient_id FROM medications WHERE id = :mid LIMIT 1),
                         :ctype, :pdos, :ndos, :rsn, 'task_agent')
                 RETURNING id"""
        db_rows = execute_write(sql, {
            "mid": medication_id, "ctype": change_type, "pdos": previous_dosage or None,
            "ndos": new_dosage or None, "rsn": reason or ""
        })
        if db_rows:
            return {
                "status": "success",
                "source": "alloydb",
                "change_type": change_type,
                "medication_id": medication_id,
                "message": f"Change logged: {change_type} for {medication_id}.",
            }
        logger.warning("log_medication_change: alloydb insert failed, using mock")

    change_log = tool_context.state.get("medication_change_log", [])
    entry = {
        "medication_id": medication_id,
        "change_type": change_type,
        "previous_dosage": previous_dosage or "",
        "new_dosage": new_dosage or "",
        "reason": reason or "",
        "logged_at": datetime.now().isoformat(),
    }
    change_log.append(entry)
    tool_context.state["medication_change_log"] = change_log

    return {
        "status": "success",
        "source": "mock",
        "change_type": change_type,
        "medication_id": medication_id,
        "message": f"Change logged: {change_type} for {medication_id}.",
    }


def _severity_to_safety(severities: list[str]) -> str:
    """RxNav severity 문자열을 내부 safety_check 레벨로 매핑.

    Map RxNav severity strings to our internal safety_check level.
    HIGH/CONTRAINDICATED/MAJOR and MODERATE/MEDIUM both surface as 'warning' —
    a MODERATE interaction still warrants clinician review.
    """
    norm = {(s or "").strip().upper() for s in severities}
    if norm & {"HIGH", "CONTRAINDICATED", "MAJOR"}:
        return "warning"
    if norm & {"MODERATE", "MEDIUM"}:
        return "warning"
    return "info"


def _max_severity(severities: list[str]) -> str:
    """severity 리스트에서 가장 심각한 레벨을 반환 (HITL payload 용).

    Pick the most severe level from a list, ordered CONTRAINDICATED > HIGH >
    MAJOR > MODERATE > MEDIUM > LOW > INFO. Used to populate the HITL trigger.
    """
    norm = {(s or "").strip().upper() for s in severities}
    for level in ("CONTRAINDICATED", "HIGH", "MAJOR", "MODERATE", "MEDIUM", "LOW"):
        if level in norm:
            return level
    return "INFO"


def _classify_interaction_severity(normalized: list[dict]) -> str:
    """severity 리스트에서 safety_check ("warning"/"info") 판정.

    CONTRAINDICATED/HIGH/MAJOR/MODERATE/MEDIUM → warning (임상의 검토 필요).
    """
    norm_sev = {(i.get("severity") or "").upper() for i in normalized}
    if norm_sev & {"CONTRAINDICATED", "HIGH", "MAJOR", "MODERATE", "MEDIUM"}:
        return "warning"
    return "info"


def _trigger_hitl_if_needed(
    tool_context: ToolContext,
    safety_status: str,
    normalized: list[dict],
    source: str,
) -> None:
    """warning 수준 상호작용 감지 시 pending_hitl state에 HITL 트리거 설정."""
    if tool_context is None or safety_status != "warning":
        return
    severities = [i.get("severity", "") for i in normalized]
    tool_context.state["pending_hitl"] = {
        "action_type": "drug_interaction_warning",
        "severity": _max_severity(severities),
        "interactions": normalized[:3],
        "source": source,
    }


def _interaction_result_envelope(
    status: str,
    new_medication: str,
    current_medications: list[str],
    safety_check: str,
    source: str,
    interactions: list[dict],
) -> dict:
    """상호작용 결과 envelope 생성 — 3 layer 공통 반환 형식."""
    return {
        "status": status,
        "new_medication": new_medication,
        "checked_against": current_medications,
        "safety_check": safety_check,
        "source": source,
        "interaction_count": len(interactions),
        "interactions": interactions,
    }


def check_drug_interactions(
    new_medication: str,
    current_medications: list[str],
    tool_context: ToolContext = None,
) -> dict:
    """3-layer 약물 상호작용 검증 (openFDA → AlloyDB DDI → 하드코딩 폴백).

    Three-layer interaction check with graceful degradation:

      Layer 1 — openFDA Drug Labels (authoritative, real-time FDA SPL data).
                Replaces the retired RxNav /interaction/list endpoint.
      Layer 2 — Local DDI corpus in AlloyDB (optional; only if table populated).
      Layer 3 — Hardcoded ``_KNOWN_INTERACTIONS`` table as last-resort offline
                fallback when both network and DB are unavailable.

    The first layer that produces a definitive answer short-circuits. Each
    layer stamps its own ``source`` so downstream audit/telemetry can tell
    where a given verdict came from.

    Args:
        new_medication: Name of the new medication to check.
        current_medications: Current meds to check against.
        tool_context: ADK ToolContext for state (audit log + HITL trigger).

    Returns:
        dict with:
          - status: "interactions_detected" | "no_interactions"
          - safety_check: "warning" | "info" | "passed"
          - source: "openfda_drug_label" | "alloydb_ddi_corpus" | "local_fallback"
          - interaction_count / interactions
    """
    # 조회 이력 기록 / Audit log entry.
    if tool_context is not None:
        check_log = tool_context.state.get("interaction_checks", [])
        check_log.append({
            "new_med": new_medication,
            "checked_against": current_medications,
            "checked_at": datetime.now().isoformat(),
        })
        tool_context.state["interaction_checks"] = check_log

    # ==================================================================
    # Layer 1 — openFDA Drug Labels (authoritative, real-time)
    # ==================================================================
    try:
        logger.info("interaction_check.layer1.openfda.start drug=%s", new_medication)
        from careflow.agents.shared.openfda_api import check_drug_interactions_via_fda

        fda_result = check_drug_interactions_via_fda(new_medication, current_medications)
        fda_status = fda_result.get("status")

        if fda_status == "checked" and fda_result.get("interaction_count", 0) > 0:
            interactions = fda_result["interactions"]
            # 정규화된 출력 스키마로 재매핑 (medication1/medication2 키 일관성).
            normalized: list[dict] = []
            for hit in interactions:
                pair = hit.get("drug_pair") or [new_medication, ""]
                normalized.append({
                    "medication1": pair[0],
                    "medication2": pair[1] if len(pair) > 1 else "",
                    "severity": hit.get("severity", "UNKNOWN"),
                    "description": hit.get("description", ""),
                    "source": hit.get("source", "openfda_drug_label"),
                })

            safety_status = _classify_interaction_severity(normalized)
            _trigger_hitl_if_needed(tool_context, safety_status, normalized, "openfda_drug_label")
            logger.info(
                "interaction_check.layer1.openfda.hit count=%d severity=%s",
                len(normalized), _max_severity([i.get("severity","") for i in normalized]),
            )
            return _interaction_result_envelope(
                "interactions_detected", new_medication, current_medications,
                safety_status, "openfda_drug_label", normalized,
            )

        if fda_status == "checked":
            # 라벨은 조회됐고 상호작용 텍스트도 있었으나 현재 약물 언급 없음 → 확정적 "안전".
            # Label retrieved and scanned, no current-drug mentions → definitive pass.
            logger.info("interaction_check.layer1.openfda.clean drug=%s", new_medication)
            return {
                "status": "no_interactions",
                "new_medication": new_medication,
                "checked_against": current_medications,
                "safety_check": "passed",
                "source": "openfda_drug_label",
                "interaction_count": 0,
                "interactions": [],
            }

        # drug_not_found / no_interaction_data → Layer 2로 진행.
        logger.info(
            "interaction_check.layer1.openfda.inconclusive status=%s → fallthrough",
            fda_status,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("interaction_check.layer1.openfda.failed: %s", e)

    # ==================================================================
    # Layer 2 — AlloyDB local DDI corpus (populated offline, if available)
    # ==================================================================
    try:
        logger.info("interaction_check.layer2.alloydb.start")
        current_lower = [d.strip().lower() for d in current_medications]
        rows = query_dict(
            """SELECT drug1, drug2, severity, description
                 FROM drug_interactions
                WHERE (LOWER(drug1) = LOWER(:d1) AND LOWER(drug2) = ANY(:d2_list))
                   OR (LOWER(drug2) = LOWER(:d1) AND LOWER(drug1) = ANY(:d2_list))""",
            {"d1": new_medication, "d2_list": current_lower},
        )
        if rows:
            normalized = [{
                "medication1": new_medication,
                "medication2": (
                    r.get("drug2")
                    if (r.get("drug1") or "").lower() == new_medication.lower()
                    else r.get("drug1")
                ),
                "severity": (r.get("severity") or "UNKNOWN").upper(),
                "description": r.get("description") or "",
                "source": "alloydb_ddi_corpus",
            } for r in rows]

            safety_status = _classify_interaction_severity(normalized)
            _trigger_hitl_if_needed(tool_context, safety_status, normalized, "alloydb_ddi_corpus")
            logger.info("interaction_check.layer2.alloydb.hit count=%d", len(normalized))
            return _interaction_result_envelope(
                "interactions_detected", new_medication, current_medications,
                safety_status, "alloydb_ddi_corpus", normalized,
            )
        logger.info("interaction_check.layer2.alloydb.empty → fallthrough")
    except Exception as e:  # noqa: BLE001
        # 테이블 미존재/DB 미기동 — Layer 3로 계속 진행.
        logger.info("interaction_check.layer2.alloydb.unavailable: %s", e)

    # ==================================================================
    # Layer 3 — Hardcoded offline fallback (last resort)
    # ==================================================================
    logger.info("interaction_check.layer3.local_fallback.start")
    new_med_lower = new_medication.strip().lower()
    interactions: list[dict] = []

    for current_med in current_medications:
        current_lower = current_med.strip().lower()
        hit = (
            _KNOWN_INTERACTIONS.get((new_med_lower, current_lower))
            or _KNOWN_INTERACTIONS.get((current_lower, new_med_lower))
        )
        if hit:
            interactions.append({
                "medication1": new_medication,
                "medication2": current_med,
                "source": "local_fallback",
                **hit,
            })

    if interactions:
        safety_check = _classify_interaction_severity(interactions)
        status = "interactions_detected"
    else:
        safety_check = "passed"
        status = "no_interactions"

    _trigger_hitl_if_needed(tool_context, safety_check, interactions, "local_fallback")
    logger.info(
        "interaction_check.layer3.local_fallback.done hits=%d safety=%s",
        len(interactions), safety_check,
    )
    return _interaction_result_envelope(
        status, new_medication, current_medications,
        safety_check, "local_fallback", interactions,
    )


def lookup_medication_info(
    medication_name: str,
) -> dict:
    """Look up a medication's profile from the reference database.

    약물의 참조 프로필 정보를 조회합니다.

    Args:
        medication_name: Name of the medication to look up.

    Returns:
        dict with medication profile info (class, uses, dosage, side effects,
        contraindications), or "not_found" status.
    """
    normalized = medication_name.strip().lower()
    info = _MEDICATION_INFO.get(normalized)

    if info:
        return {
            "status": "found",
            **info,
        }

    return {
        "status": "not_found",
        "medication_name": medication_name,
        "message": f"'{medication_name}' not found in reference database. Use clinical judgment.",
    }


def create_task(
    patient_id: str,
    description: str,
    due_date: str,
    priority: str,
    tool_context: ToolContext,
    notes: Optional[str] = None,
) -> dict:
    """Create a new task or action item for the patient.

    환자에 대한 새 태스크 또는 조치 항목을 생성합니다.

    Args:
        patient_id: Unique patient identifier.
        description: Task description (e.g. "HbA1c blood test").
        due_date: Due date in YYYY-MM-DD format.
        priority: Priority level — "low", "medium", "high", or "urgent".
        tool_context: ADK ToolContext for state management.
        notes: Optional additional notes (e.g., "fasting required").

    Returns:
        dict with "status", "task_id", and created task details.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    if _is_db_available():
        sql = """INSERT INTO tasks (patient_id, description, due_date, priority, status, created_by_agent)
                 VALUES (:pid, :desc, :due, :prio, 'pending', 'task_agent')
                 RETURNING id"""
        due_val = due_date if due_date else None
        db_rows = execute_write(sql, {
            "pid": patient_id, "desc": description + (f" (Notes: {notes})" if notes else ""),
            "due": due_val, "prio": priority
        })
        if db_rows:
            return {
                "status": "success",
                "source": "alloydb",
                "task_id": str(db_rows[0]["id"]),
                "description": description,
                "due_date": due_date,
                "priority": priority,
                "message": f"Task created: '{description}' due {due_date} (priority: {priority}).",
            }
        return {
            "status": "error",
            "source": "alloydb",
            "message": f"Failed to create task in AlloyDB.",
        }

    logger.info("create_task: alloydb unavailable, using mock")
    tasks = tool_context.state.get("tasks", [])

    task_id = _get_next_task_id()
    new_task = {
        "task_id": task_id,
        "patient_id": patient_id,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "status": "pending",
        "notes": notes or "",
        "created_at": datetime.now().isoformat(),
        "created_by_agent": "task_agent",
    }
    tasks.append(new_task)
    tool_context.state["tasks"] = tasks

    return {
        "status": "success",
        "source": "mock",
        "task_id": task_id,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "message": f"Task created: '{description}' due {due_date} (priority: {priority}).",
    }


def get_pending_tasks(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """Retrieve all pending and overdue tasks for a patient.

    환자의 대기 중/지연된 태스크를 모두 조회합니다.

    Args:
        patient_id: Unique patient identifier.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "task_count", and "tasks" list.
    """
    patient_id = _resolve_patient_id(patient_id, tool_context)
    if _is_db_available():
        sql = """SELECT * FROM tasks WHERE patient_id = :pid AND status IN ('pending', 'overdue')
                 ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date"""
        db_rows = query_dict(sql, {"pid": patient_id})
        return {
            "status": "success",
            "source": "alloydb",
            "patient_id": patient_id,
            "task_count": len(db_rows),
            "tasks": db_rows,
        }

    tasks = tool_context.state.get("tasks", [])

    # 해당 환자의 대기 태스크만 필터 / Filter pending tasks for this patient
    pending = [
        task for task in tasks
        if task.get("patient_id") == patient_id
        and task.get("status") in ("pending", "overdue")
    ]

    # 우선순위순 정렬 / Sort by priority
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    pending.sort(key=lambda t: (priority_order.get(t.get("priority", "medium"), 2), t.get("due_date", "")))

    return {
        "status": "success",
        "source": "mock",
        "patient_id": patient_id,
        "task_count": len(pending),
        "tasks": pending,
    }
