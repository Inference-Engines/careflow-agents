"""CareFlow FastAPI 프록시 서버 / FastAPI Proxy Server.

프론트엔드와 ADK 서버 사이의 프록시 + AlloyDB 데이터 API를 제공한다.
AlloyDB 연결 실패 시 목(mock) 데이터로 자동 폴백하여 오프라인 개발/데모 가능.

Acts as a proxy between the React frontend and ADK server, plus serves
AlloyDB-backed data APIs. Gracefully falls back to mock data when AlloyDB
is unavailable, enabling offline development and demo scenarios.

아키텍처 / Architecture:
  Browser (React) --> FastAPI Proxy --> ADK Server (agent orchestration)
                                    --> AlloyDB (patient data) | Mock fallback

엔드포인트 / Endpoints:
  POST /api/session      -- ADK 세션 생성 프록시
  POST /api/run          -- ADK SSE 스트리밍 프록시
  GET  /api/health       -- 헬스체크 (ADK 연결 확인 포함)
  GET  /api/metrics/*    -- 건강 지표 (AlloyDB -> mock 폴백)
  GET  /api/medications/* -- 처방 정보 (AlloyDB -> mock 폴백)
  GET  /api/appointments -- 예약 일정 (AlloyDB -> mock 폴백)
  GET  /api/visits/*     -- 방문 기록 (AlloyDB -> mock 폴백)
  GET  /api/caregiver    -- 보호자 정보 (AlloyDB -> mock 폴백)

환경변수 / Environment variables:
  ADK_BASE_URL      -- ADK 서버 주소    (default: http://localhost:8000)
  APP_NAME          -- ADK 앱 이름      (default: careflow)
  PORT              -- 리스닝 포트       (default: 8001)
  ALLOYDB_CONN_URI  -- AlloyDB 연결 문자열 (미설정 시 mock 폴백)
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import date, datetime

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from careflow.db.alloydb_client import query_dict

ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://localhost:8000")
APP_NAME = os.getenv("APP_NAME", "careflow")

# ── 복약 이행 추적 (인메모리) / In-Memory Medication Adherence ───────────────
# 세션 단위로 "오늘 복용 완료" 상태를 추적. 프로덕션에서는 AlloyDB로 대체 예정.
# Tracks "taken today" per session. Will migrate to AlloyDB in production.
_taken_today: dict[str, set[str]] = {}  # patient_id -> set of med_ids taken today

# ── 공유 HTTP 클라이언트 / Shared Async HTTP Client ─────────────────────────
# 커넥션 풀링으로 ADK 서버와의 통신 효율화. lifespan에서 생성/정리.
# Connection-pooled client for ADK server. Created/closed in lifespan.

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


# ── ADK 프록시 라우트 / ADK Proxy Routes ─────────────────────────────────────
# 프론트엔드가 ADK 서버에 직접 접근하지 않도록 프록시 계층을 둔다.
# CORS·인증을 한 곳에서 관리하고, Cloud Run 배포 시 단일 서비스로 묶기 위함.
# Proxy layer prevents direct frontend-to-ADK access.
# Centralizes CORS/auth and enables single Cloud Run service deployment.


@app.post("/api/session")
async def create_session(request: Request):
    """ADK 세션 생성 프록시 / Proxy ADK session creation.

    Body: { app_name, user_id, session_id }
    ADK endpoint: POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
    """
    if not http_client:
        return JSONResponse({"error": "Service not initialized"}, status_code=503)

    body = await request.json()
    app_name = body.get("app_name", APP_NAME)
    user_id = body.get("user_id", "default-user")
    session_id = body.get("session_id", "default-session")

    adk_url = f"/apps/{app_name}/users/{user_id}/sessions/{session_id}"

    resp = await http_client.post(adk_url, json={})
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.post("/api/run")
async def run_agent(request: Request):
    """ADK 에이전트 실행 프록시 — SSE 스트리밍 / Proxy agent run with SSE streaming.

    ADK 응답(JSON 배열)을 SSE 이벤트로 변환하여 프론트엔드에 전달.
    에이전트 활동(도구 호출, 서브에이전트 라우팅)이 실시간으로 표시된다.
    Converts ADK response (JSON array) into SSE events for the frontend.
    Agent activities (tool calls, sub-agent routing) appear in real-time.
    """
    if not http_client:
        return JSONResponse({"error": "Service not initialized"}, status_code=503)

    body = await request.json()

    async def event_stream():
        import asyncio
        # ── ADK 응답 수신 + keepalive로 브라우저 연결 유지 ──
        # ADK 처리 중 매 5초마다 SSE 코멘트를 보내 브라우저가 끊지 않게 한다.
        raw = b""
        done = False

        async def fetch_adk():
            nonlocal raw, done
            try:
                async with http_client.stream("POST", "/run", json=body, timeout=180.0) as adk_resp:
                    async for chunk in adk_resp.aiter_bytes():
                        raw += chunk
            except Exception as e:
                raw = json.dumps({"error": str(e)}).encode()
            done = True

        task = asyncio.create_task(fetch_adk())

        # keepalive: 매 5초 SSE 코멘트 전송 (브라우저 타임아웃 방지)
        while not done:
            yield ": keepalive\n\n"
            await asyncio.sleep(5)

        await task

        # Parse the accumulated response (ADK returns JSON array)
        try:
            data = json.loads(raw.decode("utf-8"))
            events = data if isinstance(data, list) else [data]
            for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except (json.JSONDecodeError, UnicodeDecodeError):
            yield f"data: {raw.decode('utf-8', errors='replace')}\n\n"
        yield "data: [DONE]\n\n"

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
    """헬스체크 — ADK 연결 상태 확인 포함 / Health check with ADK connectivity."""
    if not http_client:
        return JSONResponse({"error": "Service not initialized"}, status_code=503)
    try:
        resp = await http_client.get("/list-apps", timeout=5.0)
        return {"status": "ok", "adk_apps": resp.json()}
    except Exception as exc:
        return JSONResponse({"status": "degraded", "error": str(exc)}, status_code=503)


# ── AlloyDB 데이터 엔드포인트 / AlloyDB Data Endpoints ───────────────────────
# 모든 데이터 엔드포인트는 AlloyDB 우선 조회 → 실패 시 mock 폴백 패턴을 따른다.
# 이를 통해 AlloyDB 미설정 환경에서도 UI 데모가 가능하다.
# Every data endpoint follows AlloyDB-first → mock-fallback pattern.
# This enables UI demos even without an AlloyDB connection.

# ── 목(mock) 데이터 — 폴백용 / Mock Data for Graceful Fallback ──────────────

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
    """최신 건강 지표 조회 / Latest health metric (AlloyDB -> mock fallback)."""
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
    """건강 지표 시계열 데이터 / Time-series metrics for trend charts (AlloyDB -> mock)."""
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
    """활성 처방 목록 / Active medications (AlloyDB -> mock fallback)."""
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
    """복약 완료 기록 (인메모리) / Mark medication taken today (in-memory)."""
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
    """예약 일정 조회 / Upcoming appointments (AlloyDB -> mock fallback)."""
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
    """최근 방문 기록 / Recent visit records (AlloyDB -> mock fallback)."""
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
    """보호자 정보 조회 / Caregiver info (AlloyDB -> mock fallback)."""
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


# ── 8. GET /api/drug-interactions ───────────────────────────────────────────

_FALLBACK_INTERACTIONS = [
    {
        "drug1": "Metformin",
        "drug2": "Lisinopril",
        "severity": "MODERATE",
        "description": "Lisinopril may increase the hypoglycemic effect of Metformin. Monitor blood glucose closely, especially after dose changes.",
        "source": "openFDA Drug Label",
    },
    {
        "drug1": "Amlodipine",
        "drug2": "Atorvastatin",
        "severity": "MODERATE",
        "description": "Amlodipine may increase Atorvastatin blood levels, raising the risk of myopathy. Monitor for muscle pain or weakness.",
        "source": "openFDA Drug Label",
    },
]


@app.get("/api/drug-interactions")
async def get_drug_interactions(patient_id: str = Query(...)):
    """Check drug interactions for a patient's active medications via openFDA."""
    import ssl
    import urllib.parse
    import urllib.request

    # 1. Get active medication names
    rows = query_dict(
        """
        SELECT name FROM medications
        WHERE patient_id = :pid AND status = 'active'
        """,
        {"pid": patient_id},
    )
    med_names: list[str] = [r["name"] for r in rows] if rows else [m["name"] for m in _MOCK_MEDICATIONS]

    if len(med_names) < 2:
        return {"data": [], "source": "none"}

    # 2. For each medication, try openFDA label lookup for interactions
    interactions: list[dict] = []

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    for drug in med_names:
        other_drugs = [d for d in med_names if d != drug]
        try:
            query = f'(openfda.brand_name:"{drug}" OR openfda.generic_name:"{drug}")'
            url = f"https://api.fda.gov/drug/label.json?search={urllib.parse.quote(query)}&limit=1"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CareFlow/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
                data = json.loads(resp.read())

            results = data.get("results", []) or []
            if not results:
                continue

            label = results[0]
            interaction_text = " ".join(label.get("drug_interactions", [])).lower()
            warnings_text = " ".join(label.get("warnings", [])).lower()
            contra_text = " ".join(label.get("contraindications", [])).lower()
            combined = f"{interaction_text} {warnings_text} {contra_text}"

            for other in other_drugs:
                if other.lower() in combined:
                    if other.lower() in contra_text:
                        severity = "CONTRAINDICATED"
                    elif other.lower() in warnings_text:
                        severity = "HIGH"
                    else:
                        severity = "MODERATE"

                    idx = combined.find(other.lower())
                    snippet = combined[max(0, idx - 120): idx + 180].strip()[:300]

                    pair_key = tuple(sorted([drug, other]))
                    if not any(
                        tuple(sorted([ia["drug1"], ia["drug2"]])) == pair_key
                        for ia in interactions
                    ):
                        interactions.append({
                            "drug1": drug,
                            "drug2": other,
                            "severity": severity,
                            "description": snippet or f"Potential interaction between {drug} and {other}.",
                            "source": "openFDA Drug Label",
                        })
        except Exception:
            continue

    # 3. Fallback: if openFDA yielded nothing, use hardcoded list
    if not interactions:
        med_set = {n.lower() for n in med_names}
        interactions = [
            ia for ia in _FALLBACK_INTERACTIONS
            if ia["drug1"].lower() in med_set and ia["drug2"].lower() in med_set
        ]
        return {"data": interactions, "source": "fallback"}

    return {"data": interactions, "source": "openfda"}


# ─────────────────────────────────────────────────────────────────────────────
# Static frontend (production only — dist/ built by `npm run build`)
# ─────────────────────────────────────────────────────────────────────────────

_dist = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")
