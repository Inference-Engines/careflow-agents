# ============================================================================
# CareFlow Schedule Agent - Function Tools
# 일정 관리 에이전트 도구 함수 정의
# ============================================================================
# Mock 데이터 기반으로 동작하는 FunctionTool 모음.
# 실제 프로덕션에서는 Google Calendar MCP로 교체 예정.
#
# Tools backed by mock data for development/demo.
# In production, these will be replaced by Google Calendar MCP integration.
# ============================================================================

from datetime import datetime, timedelta
from typing import Optional

from google.adk.tools import ToolContext


# ---------------------------------------------------------------------------
# Mock Data Store
# 실제 Google Calendar 없이 동작하도록 하드코딩된 테스트 데이터
# Hardcoded test data to operate without a real Google Calendar connection
# ---------------------------------------------------------------------------

_MOCK_AVAILABLE_SLOTS = {
    # 기본 가용 시간대 (요일 무관) / Default available slots (day-independent)
    "default": [
        "07:00", "07:30", "08:00", "08:30", "09:00", "09:30",
        "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30",
    ],
}

_MOCK_EXISTING_APPOINTMENTS = [
    {
        "appointment_id": "APT-001",
        "patient_id": "patient_001",
        "title": "Routine Checkup with Dr. Patel",
        "date": "2026-04-10",
        "time": "09:00",
        "notes": "Regular quarterly checkup",
        "reminders": ["24h before", "2h before"],
    },
    {
        "appointment_id": "APT-002",
        "patient_id": "patient_001",
        "title": "HbA1c Fasting Blood Test",
        "date": "2026-04-15",
        "time": "07:30",
        "notes": "FASTING REQUIRED: Do not eat or drink anything (except water) for 8-12 hours before the test.",
        "reminders": ["24h before", "2h before"],
    },
]

# 공복 검사 키워드 목록 / Fasting test keyword list
_FASTING_KEYWORDS = [
    "hba1c", "a1c", "hemoglobin a1c",
    "fasting blood glucose", "fasting glucose", "fbg",
    "lipid panel", "cholesterol test",
    "fasting blood test",
    "metabolic panel",
]

# 자동 증가 ID 카운터 / Auto-increment ID counter
_NEXT_APT_ID = 3


# ---------------------------------------------------------------------------
# Helper Functions
# 내부 유틸리티 함수
# Internal utility functions
# ---------------------------------------------------------------------------

def _get_next_apt_id() -> str:
    """다음 예약 ID 생성 / Generate next appointment ID."""
    global _NEXT_APT_ID
    apt_id = f"APT-{_NEXT_APT_ID:03d}"
    _NEXT_APT_ID += 1
    return apt_id


def _is_fasting_test(title: str) -> bool:
    """공복 검사 여부 판별 / Determine if the appointment is a fasting test."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in _FASTING_KEYWORDS)


def _get_appointments_from_state(tool_context: ToolContext) -> list:
    """state에서 예약 목록 로드 (없으면 mock 데이터 초기화).

    Load appointments from state (initialize with mock data if empty).
    """
    appointments = tool_context.state.get("appointments")
    if appointments is None:
        # mock 데이터로 초기화 / Initialize with mock data
        appointments = [apt.copy() for apt in _MOCK_EXISTING_APPOINTMENTS]
        tool_context.state["appointments"] = appointments
    return appointments


def _save_appointments_to_state(tool_context: ToolContext, appointments: list) -> None:
    """state에 예약 목록 저장 / Save appointments list to state."""
    tool_context.state["appointments"] = appointments


# ---------------------------------------------------------------------------
# Tool Functions
# 에이전트가 호출할 수 있는 도구 함수들
# Functions callable by the LLM agent via function-calling
# ---------------------------------------------------------------------------


def check_availability(
    date: str,
    tool_context: ToolContext,
) -> dict:
    """Check available appointment slots on a given date.

    Queries the calendar for open time slots, excluding times already booked.
    In production this reads from Google Calendar via MCP.

    지정된 날짜의 가용 예약 시간대를 조회합니다.
    이미 예약된 시간을 제외한 빈 시간대를 반환합니다.

    Args:
        date: Target date in YYYY-MM-DD format (e.g. "2026-04-10").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "date", "available_slots" list, and "booked_slots" list.
    """
    # state에 조회 이력 기록 / Log query history in session state
    query_log = tool_context.state.get("availability_queries", [])
    query_log.append({
        "date": date,
        "queried_at": datetime.now().isoformat(),
    })
    tool_context.state["availability_queries"] = query_log

    appointments = _get_appointments_from_state(tool_context)

    # 해당 날짜에 예약된 시간 수집 / Collect booked times for the date
    booked_times = [
        apt["time"] for apt in appointments
        if apt["date"] == date
    ]

    # 가용 시간대에서 예약된 시간 제외 / Exclude booked times from available slots
    all_slots = _MOCK_AVAILABLE_SLOTS["default"]
    available = [slot for slot in all_slots if slot not in booked_times]

    return {
        "status": "success",
        "date": date,
        "available_slots": available,
        "booked_slots": booked_times,
        "total_available": len(available),
    }


def book_appointment(
    title: str,
    date: str,
    time: str,
    notes: str,
    tool_context: ToolContext,
) -> dict:
    """Book a new appointment on the patient's calendar.

    Creates a calendar event with the specified details. Automatically detects
    fasting tests and assigns morning slots (7-9 AM) with fasting instructions.
    Sets two reminders: 24 hours before and 2 hours before.
    In production this writes to Google Calendar via MCP.

    환자의 캘린더에 새 예약을 생성합니다.
    공복 검사 자동 감지 시 아침 7-9시에 배정하고 공복 안내를 추가합니다.
    사전 알림(1일전 + 2시간전)을 자동 설정합니다.

    Args:
        title: Appointment title (e.g. "Follow-up with Dr. Patel").
        date: Date in YYYY-MM-DD format.
        time: Time in HH:MM 24-hour format (e.g. "14:00").
        notes: Additional notes (e.g. "Bring previous lab reports").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "appointment_id", booking details, and "message".
    """
    appointments = _get_appointments_from_state(tool_context)

    # 공복 검사 여부 확인 / Check if this is a fasting test
    is_fasting = _is_fasting_test(title)
    if is_fasting:
        # 공복 검사는 7:00-9:00 AM 강제 배정 / Force 7-9 AM for fasting tests
        fasting_slots = ["07:00", "07:30", "08:00", "08:30", "09:00"]
        booked_fasting = [
            apt["time"] for apt in appointments
            if apt["date"] == date and apt["time"] in fasting_slots
        ]
        available_fasting = [s for s in fasting_slots if s not in booked_fasting]

        if available_fasting:
            time = available_fasting[0]  # 가장 이른 가용 시간 배정 / Assign earliest available
        else:
            return {
                "status": "error",
                "message": (
                    f"No fasting-test slots (7:00-9:00 AM) available on {date}. "
                    "Please choose a different date for the fasting test."
                ),
            }

        # 공복 안내 자동 추가 / Auto-append fasting instructions
        fasting_note = (
            "FASTING REQUIRED: Do not eat or drink anything (except water) "
            "for 8-12 hours before the test."
        )
        notes = f"{notes} | {fasting_note}" if notes else fasting_note

    # 충돌 확인 / Check for conflicts
    conflict = next(
        (apt for apt in appointments if apt["date"] == date and apt["time"] == time),
        None,
    )
    if conflict:
        return {
            "status": "conflict",
            "conflict_with": f"{conflict['title']} at {conflict['time']}",
            "message": (
                f"Time conflict: '{conflict['title']}' is already booked at "
                f"{conflict['time']} on {date}. Use check_availability to find open slots."
            ),
        }

    # 예약 생성 / Create appointment
    apt_id = _get_next_apt_id()
    new_appointment = {
        "appointment_id": apt_id,
        "patient_id": tool_context.state.get("current_patient_id", "patient_001"),
        "title": title,
        "date": date,
        "time": time,
        "notes": notes,
        "reminders": ["24h before", "2h before"],
    }
    appointments.append(new_appointment)
    _save_appointments_to_state(tool_context, appointments)

    return {
        "status": "success",
        "appointment_id": apt_id,
        "title": title,
        "date": date,
        "time": time,
        "notes": notes,
        "is_fasting_test": is_fasting,
        "reminders": ["24h before", "2h before"],
        "message": (
            f"Appointment '{title}' booked for {date} at {time}. "
            "Reminders set for 1 day before and 2 hours before."
        ),
    }


def list_appointments(
    patient_id: str,
    tool_context: ToolContext,
) -> dict:
    """List all upcoming appointments for a patient.

    Returns all future appointments sorted by date and time.
    In production this reads from Google Calendar via MCP.

    환자의 예정된 모든 예약 목록을 반환합니다.
    날짜 및 시간순으로 정렬된 향후 예약을 반환합니다.

    Args:
        patient_id: Unique patient identifier (e.g. "patient_001").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "patient_id", "appointment_count", and "appointments" list.
    """
    # state에 최근 조회 환자 기록 / Track last queried patient in state
    tool_context.state["last_schedule_query_patient"] = patient_id

    appointments = _get_appointments_from_state(tool_context)

    # 해당 환자의 예약만 필터 / Filter appointments for this patient
    patient_apts = [
        apt for apt in appointments
        if apt.get("patient_id") == patient_id
    ]

    # 날짜+시간순 정렬 / Sort by date + time
    patient_apts.sort(key=lambda a: (a["date"], a["time"]))

    return {
        "status": "success",
        "patient_id": patient_id,
        "appointment_count": len(patient_apts),
        "appointments": patient_apts,
    }


def cancel_appointment(
    appointment_id: str,
    tool_context: ToolContext,
) -> dict:
    """Cancel an existing appointment by its ID.

    Removes the appointment from the calendar. In production this
    deletes the event from Google Calendar via MCP.

    예약 ID를 사용하여 기존 예약을 취소합니다.
    캘린더에서 해당 예약을 삭제합니다.

    Args:
        appointment_id: The appointment ID to cancel (e.g. "APT-001").
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", cancelled appointment details, and "message".
    """
    appointments = _get_appointments_from_state(tool_context)

    # 취소 대상 검색 / Find target appointment
    target_idx = None
    for idx, apt in enumerate(appointments):
        if apt["appointment_id"] == appointment_id:
            target_idx = idx
            break

    if target_idx is None:
        return {
            "status": "error",
            "message": f"Appointment '{appointment_id}' not found. Use list_appointments to see valid IDs.",
        }

    # 예약 제거 / Remove appointment
    cancelled = appointments.pop(target_idx)
    _save_appointments_to_state(tool_context, appointments)

    # 취소 이력 기록 / Log cancellation history in state
    cancel_log = tool_context.state.get("cancellation_log", [])
    cancel_log.append({
        "appointment_id": cancelled["appointment_id"],
        "title": cancelled["title"],
        "cancelled_at": datetime.now().isoformat(),
    })
    tool_context.state["cancellation_log"] = cancel_log

    return {
        "status": "success",
        "cancelled_appointment": {
            "appointment_id": cancelled["appointment_id"],
            "title": cancelled["title"],
            "date": cancelled["date"],
            "time": cancelled["time"],
        },
        "message": f"Appointment '{cancelled['title']}' on {cancelled['date']} at {cancelled['time']} has been cancelled.",
    }


def check_conflicts(
    date: str,
    time: str,
    tool_context: ToolContext,
) -> dict:
    """Check if a specific date and time conflicts with existing appointments.

    Returns conflict details and suggests alternative slots if a conflict is found.
    In production this queries Google Calendar via MCP.

    지정된 날짜/시간이 기존 예약과 충돌하는지 확인합니다.
    충돌 발견 시 대안 시간대를 제안합니다.

    Args:
        date: Target date in YYYY-MM-DD format.
        time: Target time in HH:MM 24-hour format.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "has_conflict" bool, conflict details, and "alternative_slots".
    """
    appointments = _get_appointments_from_state(tool_context)

    # 충돌 검색 / Find conflicting appointment
    conflict = next(
        (apt for apt in appointments if apt["date"] == date and apt["time"] == time),
        None,
    )

    if conflict is None:
        return {
            "status": "success",
            "has_conflict": False,
            "date": date,
            "time": time,
            "message": f"No conflict found. {time} on {date} is available.",
        }

    # 대안 시간 제안 / Suggest alternative slots
    booked_times = [
        apt["time"] for apt in appointments
        if apt["date"] == date
    ]
    all_slots = _MOCK_AVAILABLE_SLOTS["default"]
    alternatives = [slot for slot in all_slots if slot not in booked_times][:3]

    return {
        "status": "success",
        "has_conflict": True,
        "date": date,
        "time": time,
        "conflict_with": {
            "appointment_id": conflict["appointment_id"],
            "title": conflict["title"],
            "time": conflict["time"],
        },
        "alternative_slots": alternatives,
        "message": (
            f"Conflict: '{conflict['title']}' is already booked at {time} on {date}. "
            f"Available alternatives: {', '.join(alternatives)}."
        ),
    }
