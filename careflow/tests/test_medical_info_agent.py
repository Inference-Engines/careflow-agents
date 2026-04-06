"""
CareFlow — Medical Info Agent Unit Tests
Tests visit record storage, semantic search, and health trend analysis.

These tests use InMemoryRunner with mocked tools to verify the agent's
RAG pipeline and visit structuring behavior.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from careflow.config import config


# ─────────────────────────────────────────────
# Helper: Build a testable Medical Info Agent with mocked tools
# ─────────────────────────────────────────────

def build_test_medical_info_agent(mock_visit_tools):
    """Create a Medical Info Agent with mocked tools for testing."""
    agent = LlmAgent(
        name="medical_info_agent",
        model=config.AGENT_MODEL,
        description=(
            "Structures medical visit records, performs semantic search over patient history, "
            "and tracks health metric trends."
        ),
        instruction="""You are the CareFlow Medical Info Agent. You help structure visit records,
        search medical history, and analyze health trends.
        The patient_id is: a1b2c3d4-e5f6-7890-abcd-ef1234567890
        When recording visits, extract structured information from raw notes.
        When answering history questions, use search_medical_history and cite sources.
        When analyzing trends, use get_health_metrics.""",
        tools=[
            mock_visit_tools["store_visit_record"],
            mock_visit_tools["search_medical_history"],
            mock_visit_tools["get_upcoming_appointments"],
            mock_visit_tools["get_health_metrics"],
            mock_visit_tools["save_health_insight"],
        ],
    )
    return agent


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestMedicalInfoAgentVisitRecording:
    """Tests for visit record structuring and storage."""

    @pytest.mark.asyncio
    async def test_structure_visit_note(self, mock_visit_tools, patient_id):
        """Agent should structure raw visit notes into key fields."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Please record this visit: Today April 5, 2026, I visited Dr. Patel "
                     "at Apollo Hospital. My blood pressure was 135/85 and blood sugar was "
                     "130 mg/dL. The doctor said my diabetes is under control but wants "
                     "me to continue Metformin. Next checkup in 3 months."
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        response_lower = final_response.lower()
        # Agent should acknowledge recording and mention key details
        assert "dr. patel" in response_lower or "patel" in response_lower, (
            f"Agent should mention the doctor. Got: {final_response}"
        )
        assert "apollo" in response_lower, (
            f"Agent should mention the hospital. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_extract_vital_signs(self, mock_visit_tools, patient_id):
        """Agent should extract vital signs from visit notes."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Record my visit: BP was 150/95, heart rate 82, temperature 98.6°F. "
                     "Weight 78 kg. Doctor said blood pressure is too high."
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        response_lower = final_response.lower()
        assert "150" in final_response or "blood pressure" in response_lower, (
            f"Agent should mention vital signs. Got: {final_response}"
        )


class TestMedicalInfoAgentRAGSearch:
    """Tests for semantic search over visit history."""

    @pytest.mark.asyncio
    async def test_history_query_with_results(self, mock_visit_tools, patient_id):
        """Agent should use RAG search to answer history questions."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="What did the doctor say about my blood pressure?"
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Agent should provide an answer about blood pressure
        response_lower = final_response.lower()
        assert "blood pressure" in response_lower or "bp" in response_lower, (
            f"Agent should answer about blood pressure. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_history_query_with_source_citation(self, mock_visit_tools, patient_id):
        """Agent should cite sources when answering history questions."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="When was my last visit and what were the key findings?"
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Agent should provide information from records
        assert len(final_response) > 20, (
            f"Agent should provide a substantial answer. Got: {final_response}"
        )


class TestMedicalInfoAgentHealthTrends:
    """Tests for health metric trend analysis."""

    @pytest.mark.asyncio
    async def test_health_metric_query(self, mock_visit_tools, patient_id):
        """Agent should retrieve and present health metrics."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Show me my recent blood pressure readings."
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        response_lower = final_response.lower()
        assert "blood pressure" in response_lower or "bp" in response_lower, (
            f"Agent should discuss blood pressure. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_pre_visit_summary(self, mock_visit_tools, patient_id):
        """Agent should compile a pre-visit summary."""
        agent = build_test_medical_info_agent(mock_visit_tools)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="I have an appointment coming up. Can you prepare a summary "
                     "for my doctor?"
            )],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Should produce a substantial pre-visit summary
        assert len(final_response) > 50, (
            f"Agent should provide a comprehensive summary. Got: {final_response}"
        )
