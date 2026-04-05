"""
CareFlow — Tools Package
Re-exports all tool functions from the unified tools.py module.

Import examples:
    from careflow.tools import get_current_medications, add_medication
    from careflow.tools import check_drug_interactions
    from careflow.tools import store_visit_record, search_medical_history
"""

from careflow.tools.tools import (
    # Shared / Embedding
    generate_embedding,
    format_embedding_for_sql,
    # Medication tools
    get_current_medications,
    get_medications_by_status,
    add_medication,
    update_medication_status,
    log_medication_change,
    # Task tools
    create_task,
    get_pending_tasks,
    # Visit & RAG tools
    store_visit_record,
    search_medical_history,
    get_upcoming_appointments,
    get_health_metrics,
    get_health_metrics_by_type,
    save_health_insight,
    # Schedule tools
    check_availability,
    book_appointment,
    list_upcoming_appointments,
    # Notification tools
    send_caregiver_notification,
    get_caregiver_info,
    # Safety tools
    lookup_medication_info,
    check_drug_interactions,
)

__all__ = [
    # Embedding
    "generate_embedding",
    "format_embedding_for_sql",
    # Medication
    "get_current_medications",
    "get_medications_by_status",
    "add_medication",
    "update_medication_status",
    "log_medication_change",
    # Task
    "create_task",
    "get_pending_tasks",
    # Visit & RAG
    "store_visit_record",
    "search_medical_history",
    "get_upcoming_appointments",
    "get_health_metrics",
    "get_health_metrics_by_type",
    "save_health_insight",
    # Schedule
    "check_availability",
    "book_appointment",
    "list_upcoming_appointments",
    # Notification
    "send_caregiver_notification",
    "get_caregiver_info",
    # Safety
    "lookup_medication_info",
    "check_drug_interactions",
]
