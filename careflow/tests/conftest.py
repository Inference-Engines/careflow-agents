"""
CareFlow — Test Fixtures
Shared pytest fixtures for agent testing with mock database and tools.

NOTE: This conftest adds the repo root to sys.path so that top-level
modules (config) can be imported as
standalone modules without a `careflow.` prefix.
"""

import sys
import os
import json
import asyncio
from datetime import datetime, date
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

import pytest

# ─── Add repo root to sys.path ───
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ─────────────────────────────────────────────
# Mock In-Memory Database
# ─────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """
    In-memory database simulating AlloyDB tables.
    Pre-populated with sample patient data for testing.
    """
    patient_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    caregiver_id = "c1d2e3f4-a5b6-7890-cdef-ab1234567890"

    return {
        "patients": [
            {
                "id": patient_id,
                "name": "Ramesh Kumar",
                "age": 72,
                "conditions": ["diabetes", "hypertension"],
                "caregiver_id": caregiver_id,
            }
        ],
        "caregivers": [
            {
                "id": caregiver_id,
                "name": "Priya Kumar",
                "email": "priya.kumar@gmail.com",
                "relationship": "daughter",
            }
        ],
        "medications": [
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "name": "Amlodipine",
                "dosage": "5mg",
                "frequency": "once_daily",
                "timing": "morning",
                "status": "active",
                "prescribed_date": "2026-01-15",
                "notes": "For blood pressure management",
            },
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "name": "Aspirin",
                "dosage": "75mg",
                "frequency": "once_daily",
                "timing": "after_breakfast",
                "status": "active",
                "prescribed_date": "2026-01-15",
                "notes": "Blood thinner",
            },
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "twice_daily",
                "timing": "with_meals",
                "status": "active",
                "prescribed_date": "2026-02-01",
                "notes": "For diabetes management",
            },
        ],
        "medication_changes": [],
        "tasks": [
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "description": "Blood sugar check - fasting",
                "due_date": "2026-04-10",
                "priority": "high",
                "status": "pending",
                "created_by_agent": "task_agent",
            }
        ],
        "visit_records": [
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "visit_date": "2026-04-03",
                "raw_input": "Visited Dr. Sharma at City Hospital. BP was 140/90. "
                             "Doctor advised reducing sodium intake. HbA1c was 7.2%.",
                "structured_summary": "Routine follow-up. BP elevated at 140/90. "
                                      "HbA1c 7.2% - moderate control. Advised dietary changes.",
                "doctor_name": "Dr. Sharma",
                "hospital_name": "City Hospital",
                "key_findings": {"bp": "140/90", "hba1c": "7.2%"},
                "similarity": 0.95,
            }
        ],
        "appointments": [
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "type": "follow_up",
                "title": "Diabetes Follow-up with Dr. Sharma",
                "scheduled_date": "2026-04-17T10:00:00",
                "location": "City Hospital, Room 204",
                "fasting_required": True,
                "status": "scheduled",
            }
        ],
        "health_metrics": [
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "metric_type": "blood_pressure",
                "value_primary": 140,
                "value_secondary": 90,
                "unit": "mmHg",
                "measured_at": "2026-04-03T10:00:00",
                "source": "visit",
            },
            {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "metric_type": "blood_glucose",
                "value_primary": 145,
                "value_secondary": None,
                "unit": "mg/dL",
                "measured_at": "2026-04-03T10:00:00",
                "source": "visit",
            },
        ],
        "health_insights": [],
    }


@pytest.fixture
def patient_id():
    """Default test patient ID."""
    return "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ─────────────────────────────────────────────
# Mock Tool Functions
# ─────────────────────────────────────────────

@pytest.fixture
def mock_medication_tools(mock_db, patient_id):
    """Mock medication tool functions that operate on the in-memory DB."""

    async def mock_get_current_medications(patient_id: str):
        meds = [
            m for m in mock_db["medications"]
            if m["patient_id"] == patient_id
        ]
        return json.dumps(meds, default=str)

    async def mock_get_medications_by_status(patient_id: str, status: str):
        meds = [
            m for m in mock_db["medications"]
            if m["patient_id"] == patient_id
            and m["status"] == status
        ]
        return json.dumps(meds, default=str)

    async def mock_add_medication(patient_id, name, dosage, frequency, timing="",
                                   status="active", prescribed_date="", end_date="", notes=""):
        new_med = {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "name": name,
            "dosage": dosage,
            "frequency": frequency,
            "timing": timing,
            "status": status,
        }
        mock_db["medications"].append(new_med)
        return json.dumps(new_med, default=str)

    async def mock_update_medication_status(medication_id, new_dosage=None,
                                             new_status=None, new_timing=None,
                                             new_frequency=None, new_notes=None):
        for med in mock_db["medications"]:
            if med["id"] == medication_id:
                if new_dosage:
                    med["dosage"] = new_dosage
                if new_status:
                    med["status"] = new_status
                return json.dumps(med, default=str)
        return json.dumps({"error": "Not found"})

    async def mock_log_medication_change(medication_id, patient_id, change_type,
                                          previous_dosage="", new_dosage="", reason=""):
        change = {
            "id": str(uuid4()),
            "medication_id": medication_id,
            "patient_id": patient_id,
            "change_type": change_type,
            "previous_dosage": previous_dosage,
            "new_dosage": new_dosage,
        }
        mock_db["medication_changes"].append(change)
        return json.dumps(change, default=str)

    return {
        "get_current_medications": mock_get_current_medications,
        "get_medications_by_status": mock_get_medications_by_status,
        "add_medication": mock_add_medication,
        "update_medication_status": mock_update_medication_status,
        "log_medication_change": mock_log_medication_change,
    }


@pytest.fixture
def mock_visit_tools(mock_db, patient_id):
    """Mock visit record tool functions that operate on the in-memory DB."""

    async def mock_store_visit_record(patient_id, visit_date, raw_input,
                                       structured_summary, doctor_name="",
                                       hospital_name="", key_findings="{}"):
        record = {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "visit_date": visit_date,
            "doctor_name": doctor_name,
            "hospital_name": hospital_name,
        }
        mock_db["visit_records"].append(record)
        return json.dumps(record, default=str)

    async def mock_search_medical_history(patient_id, query, top_k=5):
        # Return all records as mock results with fake similarity
        results = [
            {**r, "similarity": 0.85}
            for r in mock_db["visit_records"]
            if r["patient_id"] == patient_id
        ][:top_k]
        return json.dumps(results, default=str)

    async def mock_get_upcoming_appointments(patient_id):
        appts = [a for a in mock_db["appointments"] if a["patient_id"] == patient_id]
        return json.dumps(appts, default=str)

    async def mock_get_health_metrics(patient_id):
        metrics = [
            m for m in mock_db["health_metrics"]
            if m["patient_id"] == patient_id
        ]
        return json.dumps(metrics, default=str)

    async def mock_get_health_metrics_by_type(patient_id, metric_type):
        metrics = [
            m for m in mock_db["health_metrics"]
            if m["patient_id"] == patient_id
            and m["metric_type"] == metric_type
        ]
        return json.dumps(metrics, default=str)

    async def mock_save_health_insight(patient_id, insight_type, severity,
                                        title, content, data_range_start="",
                                        data_range_end="", supporting_data="{}"):
        insight = {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "insight_type": insight_type,
            "severity": severity,
            "title": title,
        }
        mock_db["health_insights"].append(insight)
        return json.dumps(insight, default=str)

    return {
        "store_visit_record": mock_store_visit_record,
        "search_medical_history": mock_search_medical_history,
        "get_upcoming_appointments": mock_get_upcoming_appointments,
        "get_health_metrics": mock_get_health_metrics,
        "get_health_metrics_by_type": mock_get_health_metrics_by_type,
        "save_health_insight": mock_save_health_insight,
    }


# ─────────────────────────────────────────────
# Event Loop Fixture
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
