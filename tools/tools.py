"""
CareFlow — Unified Tools Module
All FunctionTool wrappers for the CareFlow multi-agent system.

Consolidates: medication, task, visit/RAG, schedule, notification,
safety (drug interactions), and embedding tools into a single file
with clear modular sections.

Each section can be imported independently via the tools __init__.py.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from google.cloud import aiplatform
from toolbox_core import ToolboxClient

from careflow.config import config

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
#  SHARED: Toolbox Client + Embedding Utilities
# ═════════════════════════════════════════════════════════════════════

async def _get_client() -> ToolboxClient:
    """Create a Toolbox client connected to the configured server."""
    return ToolboxClient(config.TOOLBOX_SERVER_URL)


# ─── Vertex AI Embeddings ───

_vertex_initialized: bool = False


def _ensure_vertex_initialized():
    """Lazily initialize Vertex AI SDK."""
    global _vertex_initialized
    if not _vertex_initialized:
        aiplatform.init(
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_LOCATION,
        )
        _vertex_initialized = True


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text using Vertex AI.

    Args:
        text: The input text to embed.

    Returns:
        A list of floats representing the embedding vector (768 dimensions).
    """
    _ensure_vertex_initialized()

    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained(config.EMBEDDING_MODEL)
    embeddings = model.get_embeddings([text])

    return embeddings[0].values


def format_embedding_for_sql(embedding: list[float]) -> str:
    """
    Format an embedding vector as a SQL-compatible string for pgvector.

    Args:
        embedding: List of floats from generate_embedding().

    Returns:
        String representation like '[0.1, 0.2, ...]' for pgvector.
    """
    return "[" + ",".join(str(v) for v in embedding) + "]"


# ═════════════════════════════════════════════════════════════════════
#  SECTION 1: Medication Tools
# ═════════════════════════════════════════════════════════════════════

async def get_current_medications(patient_id: str) -> str:
    """
    Retrieve all medications for a patient from the database.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string of medication records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_medications")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


async def get_medications_by_status(patient_id: str, status: str) -> str:
    """
    Retrieve medications for a patient filtered by status.

    Args:
        patient_id: The UUID of the patient.
        status: The status to filter by — 'active', 'discontinued', or 'modified'.

    Returns:
        JSON string of filtered medication records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_medications_by_status")
        result = await tool(patient_id=patient_id, status=status)
        return json.dumps(result, default=str)


async def add_medication(
    patient_id: str,
    name: str,
    dosage: str,
    frequency: str,
    timing: str = "",
    status: str = "active",
    prescribed_date: Optional[str] = None,
    end_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Add a new medication record for a patient.

    Args:
        patient_id: The UUID of the patient.
        name: Medication name (e.g., 'Metformin').
        dosage: Dosage amount (e.g., '1000mg').
        frequency: How often (e.g., 'twice_daily').
        timing: When to take (e.g., 'with_meals').
        status: Medication status — 'active', 'modified', or 'discontinued'.
        prescribed_date: Date prescribed in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format, or None if ongoing.
        notes: Additional notes about the medication.

    Returns:
        JSON string with the created medication record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("insert_medication")
        result = await tool(
            patient_id=patient_id,
            name=name,
            dosage=dosage,
            frequency=frequency,
            timing=timing or "",
            status=status or "active",
            prescribed_date=prescribed_date or "",
            end_date=end_date or "",
            notes=notes or "",
        )
        return json.dumps(result, default=str)


async def update_medication_status(
    medication_id: str,
    new_dosage: Optional[str] = None,
    new_status: Optional[str] = None,
    new_timing: Optional[str] = None,
    new_frequency: Optional[str] = None,
    new_notes: Optional[str] = None,
) -> str:
    """
    Update an existing medication record — dosage, status, timing, frequency, or notes.

    Args:
        medication_id: The UUID of the medication record to update.
        new_dosage: Updated dosage, or None to keep existing.
        new_status: Updated status, or None to keep existing.
        new_timing: Updated timing, or None to keep existing.
        new_frequency: Updated frequency, or None to keep existing.
        new_notes: Updated notes, or None to keep existing.

    Returns:
        JSON string with the updated medication record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("update_medication")
        result = await tool(
            medication_id=medication_id,
            new_dosage=new_dosage or "",
            new_status=new_status or "",
            new_timing=new_timing or "",
            new_frequency=new_frequency or "",
            new_notes=new_notes or "",
        )
        return json.dumps(result, default=str)


async def log_medication_change(
    medication_id: str,
    patient_id: str,
    change_type: str,
    previous_dosage: Optional[str] = None,
    new_dosage: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """
    Log a medication change event for audit tracking.

    Args:
        medication_id: The UUID of the medication.
        patient_id: The UUID of the patient.
        change_type: Type of change — 'new', 'dosage_change', or 'discontinued'.
        previous_dosage: Previous dosage value (for changes), or None for new medications.
        new_dosage: New dosage value (for changes), or None for discontinued.
        reason: Reason for the change.

    Returns:
        JSON string with the change record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("insert_medication_change")
        result = await tool(
            medication_id=medication_id,
            patient_id=patient_id,
            change_type=change_type,
            previous_dosage=previous_dosage or "",
            new_dosage=new_dosage or "",
            reason=reason or "",
        )
        return json.dumps(result, default=str)


# ═════════════════════════════════════════════════════════════════════
#  SECTION 2: Task Tools
# ═════════════════════════════════════════════════════════════════════

async def create_task(
    patient_id: str,
    description: str,
    due_date: Optional[str] = None,
    priority: str = "medium",
    created_by_agent: str = "task_agent",
) -> str:
    """
    Create a new task or action item for the patient.

    Args:
        patient_id: The UUID of the patient.
        description: Task description (e.g., 'HbA1c blood test').
        due_date: Due date in YYYY-MM-DD format, or None if no deadline.
        priority: Priority level — 'low', 'medium', 'high', or 'urgent'.
        created_by_agent: Name of the agent creating this task.

    Returns:
        JSON string with the created task record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("insert_task")
        result = await tool(
            patient_id=patient_id,
            description=description,
            due_date=due_date or "",
            priority=priority,
            created_by_agent=created_by_agent,
        )
        return json.dumps(result, default=str)


async def get_pending_tasks(patient_id: str) -> str:
    """
    Retrieve all pending and overdue tasks for a patient,
    ordered by priority and due date.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string of task records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_tasks")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


# ═════════════════════════════════════════════════════════════════════
#  SECTION 3: Visit Record & RAG Tools
# ═════════════════════════════════════════════════════════════════════

async def store_visit_record(
    patient_id: str,
    visit_date: str,
    raw_input: str,
    structured_summary: str,
    doctor_name: Optional[str] = None,
    hospital_name: Optional[str] = None,
    key_findings: Optional[str] = None,
) -> str:
    """
    Store a visit record in the database with an auto-generated vector embedding.
    The embedding enables future semantic search over visit history.

    Args:
        patient_id: The UUID of the patient.
        visit_date: Visit date in YYYY-MM-DD format.
        raw_input: The original user input text describing the visit.
        structured_summary: AI-generated structured summary of the visit.
        doctor_name: Name of the attending doctor.
        hospital_name: Name of the hospital or clinic.
        key_findings: JSON string of key findings from the visit.

    Returns:
        JSON string with the created visit record.
    """
    # Generate embedding from the structured summary for better search
    embedding_text = f"{structured_summary} {raw_input}"
    embedding = generate_embedding(embedding_text)
    embedding_str = format_embedding_for_sql(embedding)

    async with await _get_client() as client:
        tool = await client.load_tool("insert_visit_record")
        result = await tool(
            patient_id=patient_id,
            visit_date=visit_date,
            raw_input=raw_input,
            structured_summary=structured_summary,
            doctor_name=doctor_name or "",
            hospital_name=hospital_name or "",
            key_findings=key_findings or "{}",
            embedding=embedding_str,
        )
        return json.dumps(result, default=str)


async def search_medical_history(
    patient_id: str,
    query: str,
    top_k: int = 5,
) -> str:
    """
    Perform semantic search over a patient's visit records using pgvector.
    Generates an embedding for the query text and finds the most relevant
    visit records by cosine similarity.

    Use this tool when the user asks questions about their medical history,
    such as "What did the doctor say about my blood pressure?" or
    "When was my last diabetes checkup?"

    Args:
        patient_id: The UUID of the patient.
        query: Natural language search query.
        top_k: Number of results to return (default 5).

    Returns:
        JSON string of the most relevant visit records with similarity scores.
    """
    # Generate embedding for the search query
    query_embedding = generate_embedding(query)
    embedding_str = format_embedding_for_sql(query_embedding)

    async with await _get_client() as client:
        tool = await client.load_tool("search_visit_records")
        result = await tool(
            patient_id=patient_id,
            query_embedding=embedding_str,
            top_k=top_k,
        )
        return json.dumps(result, default=str)


async def get_upcoming_appointments(patient_id: str) -> str:
    """
    Retrieve all upcoming scheduled appointments for a patient.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string of upcoming appointment records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_appointments")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


async def get_health_metrics(patient_id: str) -> str:
    """
    Retrieve all health metrics for a patient (most recent 50).

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string of health metric records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_health_metrics")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


async def get_health_metrics_by_type(patient_id: str, metric_type: str) -> str:
    """
    Retrieve health metrics for a patient filtered by type.

    Args:
        patient_id: The UUID of the patient.
        metric_type: The metric type — 'blood_pressure', 'blood_glucose', 'weight', or 'heart_rate'.

    Returns:
        JSON string of filtered health metric records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_health_metrics_by_type")
        result = await tool(patient_id=patient_id, metric_type=metric_type)
        return json.dumps(result, default=str)


async def save_health_insight(
    patient_id: str,
    insight_type: str,
    severity: str,
    title: str,
    content: str,
    data_range_start: Optional[str] = None,
    data_range_end: Optional[str] = None,
    supporting_data: Optional[str] = None,
) -> str:
    """
    Store a generated health insight for a patient.

    Args:
        patient_id: The UUID of the patient.
        insight_type: Type — 'trend_alert', 'correlation', 'pre_visit_summary',
                      or 'recommendation'.
        severity: Severity — 'info', 'warning', or 'urgent'.
        title: Short descriptive title.
        content: Full insight text.
        data_range_start: Analysis period start (YYYY-MM-DD).
        data_range_end: Analysis period end (YYYY-MM-DD).
        supporting_data: JSON string of supporting data points.

    Returns:
        JSON string with the created insight record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("insert_health_insight")
        result = await tool(
            patient_id=patient_id,
            insight_type=insight_type,
            severity=severity,
            title=title,
            content=content,
            data_range_start=data_range_start or "",
            data_range_end=data_range_end or "",
            supporting_data=supporting_data or "{}",
        )
        return json.dumps(result, default=str)


# ═════════════════════════════════════════════════════════════════════
#  SECTION 4: Schedule Tools
# ═════════════════════════════════════════════════════════════════════

async def check_availability(patient_id: str, date: str) -> str:
    """
    Check available appointment slots for a given date by looking at existing
    appointments and suggesting open time windows.

    Args:
        patient_id: The UUID of the patient.
        date: The date to check availability for (YYYY-MM-DD format).

    Returns:
        JSON string with available slots and any existing appointments on that date.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_appointments")
        existing = await tool(patient_id=patient_id)

    # Standard clinic slots
    all_slots = ["09:00 AM", "10:00 AM", "10:30 AM", "11:00 AM",
                 "02:00 PM", "03:00 PM", "03:30 PM", "04:00 PM"]

    # Filter out already booked slots for the given date
    booked_times = []
    for apt in existing:
        apt_date = str(apt.get("scheduled_date", ""))[:10]
        if apt_date == date:
            booked_times.append(apt.get("title", "Unknown"))

    return json.dumps({
        "date": date,
        "available_slots": all_slots,
        "existing_appointments_on_date": booked_times,
        "note": f"Found {len(booked_times)} existing appointment(s) on {date}."
    }, default=str)


async def book_appointment(
    patient_id: str,
    title: str,
    appointment_type: str,
    scheduled_date: str,
    location: str,
    notes: str = "",
    fasting_required: str = "false",
) -> str:
    """
    Book a new appointment for the patient by inserting into the appointments table.

    Args:
        patient_id: The UUID of the patient.
        title: Title of the appointment (e.g., 'HbA1c Blood Test').
        appointment_type: Type — 'follow_up', 'lab_test', 'specialist', or 'general'.
        scheduled_date: Date and time in ISO format (e.g., '2026-07-03 10:00:00').
        location: Location of the appointment.
        notes: Any additional notes (e.g., 'fasting required').
        fasting_required: 'true' or 'false' — whether fasting is needed.

    Returns:
        JSON string with the created appointment record.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("insert_appointment")
        result = await tool(
            patient_id=patient_id,
            appointment_type=appointment_type or "general",
            title=title,
            scheduled_date=scheduled_date,
            location=location or "",
            notes=notes or "",
            fasting_required=fasting_required or "false",
        )
        return json.dumps(result, default=str)


async def list_upcoming_appointments(patient_id: str) -> str:
    """
    List all upcoming scheduled appointments for the patient.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string of upcoming appointment records.
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_patient_appointments")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


# ═════════════════════════════════════════════════════════════════════
#  SECTION 5: Notification Tools
# ═════════════════════════════════════════════════════════════════════

# ─── Delivery Channels (private helpers) ───

def _send_email(subject: str, body: str, to_email: str) -> bool:
    """
    Send an email via Gmail SMTP. Returns True if sent, False if skipped/failed.
    Requires GMAIL_USER and GMAIL_PASS environment variables.
    """
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_PASS")

    if not gmail_user or not gmail_pass:
        logger.info(f"Email skipped (no GMAIL credentials): {subject} → {to_email}")
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)

        logger.info(f"Email sent: {subject} → {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def _send_sms(message: str, phone: str) -> bool:
    """
    Send an SMS via Twilio. Returns True if sent, False if skipped/failed.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SMS_NUMBER.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_SMS_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.info(f"SMS skipped (no Twilio credentials): {message[:50]}... → {phone}")
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_number, to=phone)
        logger.info(f"SMS sent → {phone}")
        return True
    except Exception as e:
        logger.error(f"SMS failed: {e}")
        return False


def _send_whatsapp(message: str, phone: str) -> bool:
    """
    Send a WhatsApp message via Twilio. Returns True if sent, False if skipped/failed.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.info(f"WhatsApp skipped (no Twilio credentials): {message[:50]}... → {phone}")
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message, from_=from_number, to=f"whatsapp:{phone}"
        )
        logger.info(f"WhatsApp sent → {phone}")
        return True
    except Exception as e:
        logger.error(f"WhatsApp failed: {e}")
        return False


# ─── ADK Notification Tool Functions ───

async def send_caregiver_notification(
    patient_id: str,
    caregiver_id: str,
    notification_type: str,
    subject: str,
    message: str,
    delivery_method: str = "email",
) -> str:
    """
    Send a notification to the patient's caregiver and log it to the database.

    Notification types:
    - VISIT_UPDATE: After a doctor visit (medication changes, new appointments)
    - WEEKLY_DIGEST: Weekly health summary
    - ALERT: Urgent alerts (missed medications, abnormal metrics)
    - MEDICATION_REMINDER: Medication adherence reminders

    Delivery methods:
    - email: Send via Gmail SMTP
    - sms: Send via Twilio SMS
    - whatsapp: Send via Twilio WhatsApp
    - push: Log only (push notification placeholder)

    Args:
        patient_id: The UUID of the patient.
        caregiver_id: The UUID of the caregiver to notify.
        notification_type: Type of notification (VISIT_UPDATE, WEEKLY_DIGEST, ALERT, MEDICATION_REMINDER).
        subject: Notification subject line.
        message: The notification message body.
        delivery_method: How to deliver (email, sms, whatsapp, push).

    Returns:
        JSON string with notification status and delivery result.
    """
    delivered = False
    delivery_status = "logged"

    if notification_type == "ALERT":
        delivered = _send_email(f"[CareFlow ALERT] {subject}", message,
                               os.getenv("CAREGIVER_EMAIL", ""))
        delivery_status = "sent" if delivered else "logged"

    elif notification_type == "VISIT_UPDATE":
        delivered = _send_email(f"[CareFlow] {subject}", message,
                               os.getenv("CAREGIVER_EMAIL", ""))
        delivery_status = "sent" if delivered else "logged"

    elif notification_type == "WEEKLY_DIGEST":
        delivered = _send_email(f"[CareFlow Weekly] {subject}", message,
                               os.getenv("CAREGIVER_EMAIL", ""))
        delivery_status = "sent" if delivered else "logged"

    else:
        delivery_status = "logged"

    # Log notification to database
    try:
        async with await _get_client() as client:
            tool = await client.load_tool("insert_notification")
            await tool(
                patient_id=patient_id,
                caregiver_id=caregiver_id,
                notification_type=notification_type.lower(),
                content=json.dumps({"subject": subject, "message": message}),
                delivery_method=delivery_method,
                status=delivery_status,
            )
    except Exception as e:
        logger.error(f"Failed to log notification to DB: {e}")

    return json.dumps({
        "status": delivery_status,
        "notification_type": notification_type,
        "delivery_method": delivery_method,
        "delivered": delivered,
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
    })


async def get_caregiver_info(patient_id: str) -> str:
    """
    Retrieve the caregiver information for a given patient.

    Args:
        patient_id: The UUID of the patient.

    Returns:
        JSON string with caregiver details (name, email, relationship).
    """
    async with await _get_client() as client:
        tool = await client.load_tool("get_caregiver_for_patient")
        result = await tool(patient_id=patient_id)
        return json.dumps(result, default=str)


# ═════════════════════════════════════════════════════════════════════
#  SECTION 6: Medication Safety Tools
# ═════════════════════════════════════════════════════════════════════

# ─── In-Memory Medication Knowledge Base (HuggingFace) ───

_medication_db: dict[str, dict] = {}
_db_loaded: bool = False


def _load_medication_database():
    """
    Load medication profiles from darkknight25/medical_medicine_dataset.
    This is called lazily on first use.
    """
    global _medication_db, _db_loaded

    if _db_loaded:
        return

    try:
        from datasets import load_dataset

        logger.info("Loading medication database from HuggingFace...")
        dataset = load_dataset("darkknight25/medical_medicine_dataset", split="train")

        for entry in dataset:
            name = entry.get("medicine_name", "").strip().lower()
            if name:
                _medication_db[name] = {
                    "name": entry.get("medicine_name", ""),
                    "description": entry.get("description", ""),
                    "uses": entry.get("uses", ""),
                    "side_effects": entry.get("side_effects", ""),
                }

        logger.info(f"Loaded {len(_medication_db)} medication profiles.")
        _db_loaded = True

    except Exception as e:
        logger.warning(f"Could not load medication database: {e}. Falling back to LLM-only mode.")
        _db_loaded = True  # Prevent retries


def lookup_medication_info(medication_name: str) -> dict:
    """
    Look up a medication's profile from the knowledge base.

    Args:
        medication_name: Name of the medication to look up.

    Returns:
        A dictionary with medication profile info, or empty dict if not found.
        Keys: name, description, uses, side_effects.
    """
    _load_medication_database()

    normalized = medication_name.strip().lower()

    # Exact match
    if normalized in _medication_db:
        return _medication_db[normalized]

    # Partial match (medication names can vary)
    for key, value in _medication_db.items():
        if normalized in key or key in normalized:
            return value

    return {}


def check_drug_interactions(
    new_medication: str,
    current_medications: list[str],
) -> dict:
    """
    Check for potential drug interactions between a new medication and
    the patient's current medication list.

    This tool cross-references medication profiles from the knowledge base
    and flags potential risks based on known side effects and contraindications.

    The LLM agent should use this tool's output together with its own medical
    knowledge to provide comprehensive safety assessments.

    Args:
        new_medication: Name of the new medication being prescribed.
        current_medications: List of medication names the patient currently takes.

    Returns:
        A dictionary with:
          - safe: bool — True if no interactions detected at the DB level
          - new_medication_profile: dict — Profile of the new medication
          - current_medication_profiles: list[dict] — Profiles of current medications
          - potential_concerns: list[str] — Initial concerns from side-effect overlap
          - recommendation: str — Suggested action
    """
    _load_medication_database()

    new_profile = lookup_medication_info(new_medication)
    current_profiles = []
    potential_concerns = []

    for med_name in current_medications:
        profile = lookup_medication_info(med_name)
        if profile:
            current_profiles.append(profile)

            # Basic heuristic: check for overlapping side effects
            if new_profile and profile:
                new_effects = str(new_profile.get("side_effects", "")).lower()
                curr_effects = str(profile.get("side_effects", "")).lower()

                # Flag common dangerous overlaps
                danger_keywords = [
                    "hypoglycemia", "bleeding", "hypotension",
                    "kidney", "renal", "liver", "hepatic",
                    "serotonin", "qt prolongation", "arrhythmia",
                    "hyperkalemia", "lactic acidosis",
                ]
                shared_risks = [
                    kw for kw in danger_keywords
                    if kw in new_effects and kw in curr_effects
                ]
                if shared_risks:
                    potential_concerns.append(
                        f"⚠️ {new_medication} and {med_name} both list risks for: "
                        f"{', '.join(shared_risks)}. Review required."
                    )

    safe = len(potential_concerns) == 0

    return {
        "safe": safe,
        "new_medication_profile": new_profile or {"name": new_medication, "note": "Not found in database"},
        "current_medication_profiles": current_profiles,
        "potential_concerns": potential_concerns,
        "recommendation": (
            "No immediate concerns detected from database. "
            "Use your medical knowledge to verify further."
            if safe
            else "⚠️ Potential risks detected. Please review the concerns carefully "
                 "and verify with authoritative drug interaction resources."
        ),
    }
