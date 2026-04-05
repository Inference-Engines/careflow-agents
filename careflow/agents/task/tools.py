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

from datetime import datetime
from typing import Optional

from google.adk.tools import ToolContext


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

# 알려진 약물 상호작용 데이터베이스 (DM2 + HTN 환자용)
# Known drug interaction database (for DM2 + HTN patients)
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

# 자동 증가 ID 카운터 / Auto-increment ID counters
_NEXT_MED_ID = len(_MOCK_MEDICATIONS) + 1
_NEXT_TASK_ID = 1


# ---------------------------------------------------------------------------
# Helper Functions
# 내부 유틸리티 함수 / Internal utility functions
# ---------------------------------------------------------------------------

def _get_next_med_id() -> str:
    """다음 약물 ID 생성 / Generate next medication ID."""
    global _NEXT_MED_ID
    med_id = f"MED-{_NEXT_MED_ID:03d}"
    _NEXT_MED_ID += 1
    return med_id


def _get_next_task_id() -> str:
    """다음 태스크 ID 생성 / Generate next task ID."""
    global _NEXT_TASK_ID
    task_id = f"TASK-{_NEXT_TASK_ID:03d}"
    _NEXT_TASK_ID += 1
    return task_id


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
    medications = _get_medications_from_state(tool_context)

    patient_meds = [
        med for med in medications
        if med.get("patient_id") == patient_id
    ]

    return {
        "status": "success",
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
        "change_type": change_type,
        "medication_id": medication_id,
        "message": f"Change logged: {change_type} for {medication_id}.",
    }


def check_drug_interactions(
    new_medication: str,
    current_medications: list[str],
    tool_context: ToolContext,
) -> dict:
    """Check for drug interactions between a new medication and current ones.

    Rules-based interaction checking using a known interaction database.
    In production, supplements with RxNorm / DrugBank API lookups.

    새 약물과 현재 약물 간의 약물 상호작용을 확인합니다.

    Args:
        new_medication: Name of the new medication to check.
        current_medications: List of current medication names to check against.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "interactions_found" count, "interactions" list,
        and overall "safety_check" result.
    """
    # 상호작용 조회 이력 기록 / Log interaction check history
    check_log = tool_context.state.get("interaction_checks", [])
    check_log.append({
        "new_med": new_medication,
        "checked_against": current_medications,
        "checked_at": datetime.now().isoformat(),
    })
    tool_context.state["interaction_checks"] = check_log

    new_med_lower = new_medication.strip().lower()
    interactions = []

    for current_med in current_medications:
        current_lower = current_med.strip().lower()

        # 양방향 조회 / Bidirectional lookup
        key1 = (new_med_lower, current_lower)
        key2 = (current_lower, new_med_lower)

        interaction = _KNOWN_INTERACTIONS.get(key1) or _KNOWN_INTERACTIONS.get(key2)
        if interaction:
            interactions.append({
                "medication1": new_medication,
                "medication2": current_med,
                **interaction,
            })

    # 전체 안전 판정 / Overall safety determination
    if any(i["severity"] == "HIGH" for i in interactions):
        safety_check = "warning"
    elif interactions:
        safety_check = "info"
    else:
        safety_check = "passed"

    return {
        "status": "success",
        "new_medication": new_medication,
        "checked_against": current_medications,
        "interactions_found": len(interactions),
        "interactions": interactions,
        "safety_check": safety_check,
    }


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
        "patient_id": patient_id,
        "task_count": len(pending),
        "tasks": pending,
    }
