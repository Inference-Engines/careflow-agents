"""
server.py — CareFlow FastAPI Proxy Server

Responsibilities:
  1. Proxy /api/session  →  ADK server POST session creation
  2. Proxy /api/run      →  ADK server SSE streaming run endpoint
  3. AlloyDB data endpoints for health metrics, medications, appointments
  4. Serve Vite build (dist/) as static files (production)

Environment variables:
  ADK_BASE_URL      — ADK server address  (default: http://localhost:8000)
  APP_NAME          — ADK app name        (default: careflow)
  PORT              — port to listen on   (default: 8001)
  ALLOYDB_CONN_URI  — AlloyDB connection string (optional; falls back to mock)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, datetime

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from careflow.db.alloydb_client import query_dict

ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://localhost:8000")
APP_NAME = os.getenv("APP_NAME", "careflow")

# ─────────────────────────────────────────────────────────────────────────────
# In-memory medication adherence tracking (session-scoped)
# ─────────────────────────────────────────────────────────────────────────────

_taken_today: dict[str, set[str]] = {}  # patient_id -> set of med_ids taken today

# ─────────────────────────────────────────────────────────────────────────────
# Shared async HTTP client (reused across requests for connection pooling)
# ─────────────────────────────────────────────────────────────────────────────

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    global http_client
    http_client = httpx.AsyncClient(base_url=ADK_BASE_URL, timeout=120.0)
    yield
    await http_client.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="CareFlow Proxy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production to your Cloud Run frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# ADK Proxy Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/api/session")
async def create_session(request: Request):
    """Create an ADK session.

    Body: { app_name, user_id, session_id }
    ADK endpoint: POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
    """
    assert http_client is not None

    body = await request.json()
    app_name = body.get("app_name", APP_NAME)
    user_id = body.get("user_id", "default-user")
    session_id = body.get("session_id", "default-session")

    adk_url = f"/apps/{app_name}/users/{user_id}/sessions/{session_id}"

    resp = await http_client.post(adk_url, json={})
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.post("/api/run")
async def run_agent(request: Request):
    """Proxy an agent run request, streaming back SSE events.

    Body follows ADK RunRequest schema:
      { app_name, user_id, session_id, new_message, streaming }
    """
    assert http_client is not None

    body = await request.json()

    async def event_stream():
        async with http_client.stream("POST", "/run", json=body) as adk_resp:
            async for chunk in adk_resp.aiter_bytes():
                yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering on Cloud Run
        },
    )


@app.get("/api/health")
async def health():
    """Health check — also forwards to ADK to verify connectivity."""
    assert http_client is not None
    try:
        resp = await http_client.get("/list-apps", timeout=5.0)
        return {"status": "ok", "adk_apps": resp.json()}
    except Exception as exc:
        return JSONResponse({"status": "degraded", "error": str(exc)}, status_code=503)


# ─────────────────────────────────────────────────────────────────────────────
# AlloyDB Data Endpoints
# ─────────────────────────────────────────────────────────────────────────────


# ── Mock data for graceful fallback ──────────────────────────────────────────

_MOCK_METRICS = {
    "blood_pressure": {
        "value_primary": 128.0, "value_secondary": 82.0,
        "unit": "mmHg", "measured_at": "2026-04-07T08:00:00",
    },
    "blood_sugar": {
        "value_primary": 145.0, "value_secondary": None,
        "unit": "mg/dL", "measured_at": "2026-04-07T07:30:00",
    },
    "weight": {
        "value_primary": 68.5, "value_secondary": None,
        "unit": "kg", "measured_at": "2026-04-06T07:00:00",
    },
    "heart_rate": {
        "value_primary": 72.0, "value_secondary": None,
        "unit": "bpm", "measured_at": "2026-04-07T08:00:00",
    },
}

_MOCK_MEDICATIONS = [
    {
        "id": "med-001", "name": "Metformin", "dosage": "500mg",
        "frequency": "twice daily", "timing": "with meals",
        "prescribed_date": "2026-01-15", "notes": "Take with food",
    },
    {
        "id": "med-002", "name": "Lisinopril", "dosage": "10mg",
        "frequency": "once daily", "timing": "morning",
        "prescribed_date": "2026-02-01", "notes": "Monitor blood pressure",
    },
    {
        "id": "med-003", "name": "Atorvastatin", "dosage": "20mg",
        "frequency": "once daily", "timing": "evening",
        "prescribed_date": "2026-01-15", "notes": None,
    },
]

_MOCK_APPOINTMENTS = [
    {
        "id": "apt-001", "title": "Endocrinology Follow-up",
        "date": "2026-04-15", "time": "10:00", "doctor": "Dr. Mehta",
        "location": "Apollo Clinic, Mumbai", "type": "checkup",
        "note": "Bring recent blood sugar logs", "fasting_required": False,
        "status": "scheduled",
    },
    {
        "id": "apt-002", "title": "HbA1c Blood Test",
        "date": "2026-04-18", "time": "08:00", "doctor": "Dr. Mehta",
        "location": "SRL Diagnostics, Mumbai", "type": "lab",
        "note": "No fasting needed for HbA1c", "fasting_required": False,
        "status": "scheduled",
    },
]

_MOCK_VISITS = [
    {
        "id": "visit-001", "date": "2026-03-18",
        "type": "checkup", "doctor": "Dr. Mehta",
        "title": "Interim visit for rising home BP readings",
        "summary": "BP 142/90. Advised continued Amlodipine + Lisinopril. Re-evaluate in 4 weeks.",
        "location": "Apollo Clinic, Mumbai",
    },
    {
        "id": "visit-002", "date": "2026-02-20",
        "type": "lab", "doctor": "Dr. Mehta",
        "summary": "Quarterly blood panel. All values within acceptable range.",
        "notes": None,
    },
]

_MOCK_CAREGIVER = {
    "id": "cg-001", "name": "Park Jiyeon", "relationship": "daughter",
    "phone": "010-1234-5678", "email": "jiyeon.park@example.com",
    "is_primary": True,
}


# ── 1. GET /api/metrics/latest ───────────────────────────────────────────────

@app.get("/api/metrics/latest")
async def get_latest_metric(patient_id: str, type: str):
    """Return the most recent health metric value for a given type."""
    rows = query_dict(
        """
        SELECT value_primary, value_secondary, unit, measured_at
        FROM health_metrics
        WHERE patient_id = :pid AND metric_type = :type
        ORDER BY measured_at DESC
        LIMIT 1
        """,
        {"pid": patient_id, "type": type},
    )
    if rows:
        row = rows[0]
        # Map DB field names to frontend-expected names
        data = {
            "value": str(row.get("value_primary", "")),
            "value_secondary": str(row.get("value_secondary", "")) if row.get("value_secondary") else None,
            "unit": row.get("unit", ""),
            "recorded_at": row.get("measured_at", ""),
        }
        # For blood_pressure, format as "systolic/diastolic"
        if type == "blood_pressure" and data["value_secondary"]:
            data["value"] = f"{row.get('value_primary', '')}/{row.get('value_secondary', '')}"
        return {"data": data, "source": "alloydb"}

    # Fallback to mock
    mock = _MOCK_METRICS.get(type)
    if mock:
        return {"data": mock, "source": "mock"}
    return JSONResponse({"error": f"Unknown metric type: {type}"}, status_code=404)


# ── 2. GET /api/metrics/trend ────────────────────────────────────────────────

@app.get("/api/metrics/trend")
async def get_metric_trend(patient_id: str, type: str, days: int = 90):
    """Return time-series metric data for charts."""
    rows = query_dict(
        """
        SELECT measured_at, value_primary, value_secondary
        FROM health_metrics
        WHERE patient_id = :pid AND metric_type = :type
          AND measured_at >= NOW() - make_interval(days => :days)
        ORDER BY measured_at ASC
        """,
        {"pid": patient_id, "type": type, "days": days},
    )
    if rows:
        # Map to frontend-expected format: { day, value, recorded_at }
        mapped = []
        for i, row in enumerate(rows):
            mapped.append({
                "day": i + 1,
                "value": float(row.get("value_primary", 0)),
                "recorded_at": row.get("measured_at", ""),
            })
        return {"data": mapped, "count": len(mapped), "source": "alloydb"}

    # Fallback: generate simple mock trend
    from datetime import timedelta
    import random

    base = _MOCK_METRICS.get(type)
    if not base:
        return {"data": [], "count": 0, "source": "mock"}

    mock_trend = []
    now = datetime(2026, 4, 7, 8, 0, 0)
    base_val = base["value_primary"]
    for i in range(min(days, 30)):
        dt = now - timedelta(days=(min(days, 30) - 1 - i))
        mock_trend.append({
            "measured_at": dt.isoformat(),
            "value_primary": round(base_val + random.uniform(-5, 5), 1),
            "value_secondary": base.get("value_secondary"),
        })
    return {"data": mock_trend, "count": len(mock_trend), "source": "mock"}


# ── 3. GET /api/medications/active ───────────────────────────────────────────

@app.get("/api/medications/active")
async def get_active_medications(patient_id: str):
    """Return active medications for a patient."""
    rows = query_dict(
        """
        SELECT id, name, dosage, frequency, timing, prescribed_date, notes
        FROM medications
        WHERE patient_id = :pid AND status = 'active'
        """,
        {"pid": patient_id},
    )
    if rows:
        # Map DB fields to frontend-expected names + annotate taken status
        taken = _taken_today.get(patient_id, set())
        mapped = []
        for med in rows:
            mapped.append({
                "id": med.get("id", ""),
                "name": med.get("name", ""),
                "dose": med.get("dosage", ""),
                "schedule": f"{med.get('frequency', '')} — {med.get('timing', '')}",
                "taken_today": med.get("id", "") in taken,
                "prescribed_date": med.get("prescribed_date", ""),
                "notes": med.get("notes", ""),
            })
        return {"data": mapped, "source": "alloydb"}

    # Fallback to mock
    taken = _taken_today.get(patient_id, set())
    meds = [{
        "id": m["id"], "name": m["name"], "dose": m.get("dosage", ""),
        "schedule": f"{m.get('frequency', '')} — {m.get('timing', '')}",
        "taken_today": m["id"] in taken,
        "prescribed_date": m.get("prescribed_date", ""),
        "notes": m.get("notes", ""),
    } for m in _MOCK_MEDICATIONS]
    return {"data": meds, "source": "mock"}


# ── 4. POST /api/medications/{med_id}/mark-taken ────────────────────────────

@app.post("/api/medications/{med_id}/mark-taken")
async def mark_medication_taken(med_id: str, patient_id: str):
    """Mark a medication as taken today (in-memory session tracking)."""
    if patient_id not in _taken_today:
        _taken_today[patient_id] = set()
    _taken_today[patient_id].add(med_id)
    return {
        "status": "ok",
        "med_id": med_id,
        "patient_id": patient_id,
        "taken_today": sorted(_taken_today[patient_id]),
    }


# ── 5. GET /api/appointments ────────────────────────────────────────────────

@app.get("/api/appointments")
async def get_appointments(patient_id: str):
    """Return upcoming scheduled appointments."""
    rows = query_dict(
        """
        SELECT id, type, title, scheduled_date, location, notes,
               fasting_required, status
        FROM appointments
        WHERE patient_id = :pid AND status = 'scheduled'
        ORDER BY scheduled_date ASC
        """,
        {"pid": patient_id},
    )
    if rows:
        # Map DB fields to frontend-expected names
        mapped = []
        for apt in rows:
            sched = apt.get("scheduled_date", "")
            date_str = sched[:10] if isinstance(sched, str) else str(sched)[:10]
            time_str = sched[11:16] if isinstance(sched, str) and len(sched) > 11 else "09:00"
            mapped.append({
                "id": apt.get("id", ""),
                "title": apt.get("title", ""),
                "date": date_str,
                "time": time_str,
                "doctor": "Dr. Mehta",
                "location": apt.get("location", ""),
                "status": apt.get("status", "scheduled"),
                "type": apt.get("type", ""),
                "note": apt.get("notes", ""),
                "fasting_required": apt.get("fasting_required", False),
            })
        return {"data": mapped, "source": "alloydb"}

    return {"data": _MOCK_APPOINTMENTS, "source": "mock"}


# ── 6. GET /api/visits/recent ───────────────────────────────────────────────

@app.get("/api/visits/recent")
async def get_recent_visits(patient_id: str, limit: int = 5):
    """Return recent visit records."""
    rows = query_dict(
        """
        SELECT id, visit_date, type, provider, summary, notes
        FROM visits
        WHERE patient_id = :pid
        ORDER BY visit_date DESC
        LIMIT :lim
        """,
        {"pid": patient_id, "lim": limit},
    )
    if rows:
        return {"data": rows, "source": "alloydb"}

    return {"data": _MOCK_VISITS[:limit], "source": "mock"}


# ── 7. GET /api/caregiver ──────────────────────────────────────────────────

@app.get("/api/caregiver")
async def get_caregiver(patient_id: str):
    """Return caregiver info for a patient."""
    rows = query_dict(
        """
        SELECT id, name, relationship, phone, email, is_primary
        FROM caregivers
        WHERE patient_id = :pid AND is_primary = true
        LIMIT 1
        """,
        {"pid": patient_id},
    )
    if rows:
        return {"data": rows[0], "source": "alloydb"}

    return {"data": _MOCK_CAREGIVER, "source": "mock"}


# ─────────────────────────────────────────────────────────────────────────────
# Static frontend (production only — dist/ built by `npm run build`)
# ─────────────────────────────────────────────────────────────────────────────

_dist = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")
