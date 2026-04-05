"""
CareFlow — Output Schemas
Pydantic models for structured agent outputs.
These define the JSON contract between agents and the orchestrator.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Task Agent Output Schemas
# ─────────────────────────────────────────────

class DrugInteraction(BaseModel):
    """A detected drug interaction warning."""
    conflicting_drug: str = Field(description="Name of the drug that conflicts")
    severity: str = Field(description="Severity: low, moderate, high")
    description: str = Field(description="Description of the interaction risk")


class MedicationResult(BaseModel):
    """A single medication extracted/processed by the Task Agent."""
    name: str = Field(description="Medication name (generic)")
    dosage: str = Field(description="Dosage, e.g. '1000mg'")
    frequency: str = Field(description="Frequency, e.g. 'twice_daily'")
    timing: str = Field(default="", description="Timing, e.g. 'with_meals'")
    status: str = Field(description="Status: new, modified, discontinued, active")
    previous_dosage: Optional[str] = Field(default=None, description="Previous dosage if modified")
    safety_check: str = Field(description="Result: passed, warning, failed")
    interactions: list[DrugInteraction] = Field(default_factory=list, description="Detected interactions")


class TaskResult(BaseModel):
    """A single task/action item extracted by the Task Agent."""
    description: str = Field(description="Task description")
    due_date: Optional[str] = Field(default=None, description="Due date YYYY-MM-DD")
    priority: str = Field(default="medium", description="Priority: low, medium, high, urgent")
    notes: Optional[str] = Field(default=None, description="Additional notes, e.g. 'fasting required'")


class TaskAgentOutput(BaseModel):
    """Complete output from the Task Agent."""
    medications: list[MedicationResult] = Field(default_factory=list, description="Extracted medications")
    tasks: list[TaskResult] = Field(default_factory=list, description="Extracted tasks and action items")
    warnings: list[str] = Field(default_factory=list, description="General warnings or alerts")


# ─────────────────────────────────────────────
# Medical Info Agent Output Schemas
# ─────────────────────────────────────────────

class VisitSummary(BaseModel):
    """Structured summary of a medical visit."""
    visit_date: str = Field(description="Visit date YYYY-MM-DD")
    doctor_name: Optional[str] = Field(default=None)
    hospital_name: Optional[str] = Field(default=None)
    chief_complaint: Optional[str] = Field(default=None)
    diagnosis: list[str] = Field(default_factory=list)
    vital_signs: dict = Field(default_factory=dict, description="e.g. {'bp': '140/90', 'heart_rate': '78'}")
    medications_prescribed: list[str] = Field(default_factory=list)
    follow_up_instructions: list[str] = Field(default_factory=list)
    key_findings: dict = Field(default_factory=dict)


class RAGSearchResult(BaseModel):
    """A single result from semantic search over visit records."""
    visit_date: str
    summary: str
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    similarity_score: float = Field(description="Cosine similarity 0-1")
    source_id: str = Field(description="Visit record UUID")


class MedicalInfoOutput(BaseModel):
    """Output from the Medical Info Agent."""
    answer: str = Field(description="Natural language answer to the user query")
    sources: list[RAGSearchResult] = Field(default_factory=list, description="Source visit records used")
    visit_summary: Optional[VisitSummary] = Field(default=None, description="If a visit was just recorded")
    health_trends: Optional[dict] = Field(default=None, description="Health metric trends if analyzed")
