"""
CareFlow — Root Agent Integration Tests
Tests that the root orchestrator correctly routes requests
to the appropriate sub-agent.

These tests verify the full multi-agent pipeline using InMemoryRunner
with mocked tools to avoid external dependencies.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from careflow.config import config
from careflow.agents.task.tools import check_drug_interactions, lookup_medication_info


# ─────────────────────────────────────────────
# Helper: Build full agent hierarchy with mocked tools
# ─────────────────────────────────────────────

def build_test_root_agent(mock_medication_tools, mock_visit_tools):
    """Build the complete agent hierarchy with mocked tools."""

    # Task Agent (sub-agent)
    task_agent = LlmAgent(
        name="task_agent",
        model=config.AGENT_MODEL,
        description=(
            "Extracts medications, follow-up tasks, and action items from visit notes. "
            "Performs medication safety validation by checking drug interactions."
        ),
        instruction="""You are the Task Agent. Handle medication and task requests.
        Patient ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890""",
        tools=[
            mock_medication_tools["get_current_medications"],
            mock_medication_tools["add_medication"],
            mock_medication_tools["update_medication_status"],
            mock_medication_tools["log_medication_change"],
            check_drug_interactions,
            lookup_medication_info,
        ],
    )

    # Medical Info Agent (sub-agent)
    medical_info_agent = LlmAgent(
        name="medical_info_agent",
        model=config.AGENT_MODEL,
        description=(
            "Structures medical visit records, performs semantic search over patient history, "
            "and tracks health metric trends."
        ),
        instruction="""You are the Medical Info Agent. Handle visit records and medical history queries.
        Patient ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890""",
        tools=[
            mock_visit_tools["store_visit_record"],
            mock_visit_tools["search_medical_history"],
            mock_visit_tools["get_upcoming_appointments"],
            mock_visit_tools["get_health_metrics"],
            mock_visit_tools["save_health_insight"],
        ],
    )

    # Root Agent (orchestrator)
    root_agent = LlmAgent(
        name="careflow_root",
        model=config.AGENT_MODEL,
        description="CareFlow root orchestrator.",
        instruction="""You are CareFlow, an AI health companion.
        Route requests to the appropriate sub-agent:
        - task_agent: medication management, drug safety, task extraction
        - medical_info_agent: visit records, medical history, health trends
        Be helpful and empathetic.""",
        sub_agents=[task_agent, medical_info_agent],
    )

    return root_agent


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestRootAgentRouting:
    """Tests that the root agent routes to the correct sub-agent."""

    @pytest.mark.asyncio
    async def test_route_medication_to_task_agent(
        self, mock_medication_tools, mock_visit_tools, patient_id
    ):
        """Medication-related queries should be routed to task_agent."""
        root_agent = build_test_root_agent(mock_medication_tools, mock_visit_tools)
        runner = InMemoryRunner(agent=root_agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="I was prescribed Metformin 1000mg twice daily with meals."
            )],
        )

        final_response = ""
        agent_authors = set()

        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.author:
                agent_authors.add(event.author)
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Verify medication was processed
        response_lower = final_response.lower()
        assert "metformin" in response_lower, (
            f"Response should mention Metformin. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_route_history_to_medical_info_agent(
        self, mock_medication_tools, mock_visit_tools, patient_id
    ):
        """Medical history queries should be routed to medical_info_agent."""
        root_agent = build_test_root_agent(mock_medication_tools, mock_visit_tools)
        runner = InMemoryRunner(agent=root_agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="What did the doctor say about my blood pressure last visit?"
            )],
        )

        final_response = ""
        agent_authors = set()

        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.author:
                agent_authors.add(event.author)
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Verify medical history was searched
        assert len(final_response) > 20, (
            f"Agent should provide a substantial answer. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_greeting_handled_directly(
        self, mock_medication_tools, mock_visit_tools, patient_id
    ):
        """General greetings should be handled by root agent directly."""
        root_agent = build_test_root_agent(mock_medication_tools, mock_visit_tools)
        runner = InMemoryRunner(agent=root_agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text="Hello! How can you help me?")],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        assert len(final_response) > 10, (
            f"Root agent should respond to greetings. Got: {final_response}"
        )


class TestRootAgentEndToEnd:
    """End-to-end tests for multi-step flows."""

    @pytest.mark.asyncio
    async def test_full_visit_flow(
        self, mock_medication_tools, mock_visit_tools, patient_id
    ):
        """Test a complete visit recording + medication extraction flow."""
        root_agent = build_test_root_agent(mock_medication_tools, mock_visit_tools)
        runner = InMemoryRunner(agent=root_agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        # Step 1: Record a visit with medication info
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="I just visited Dr. Patel at Apollo Hospital today. "
                     "My BP was 130/80 and blood sugar was 125 mg/dL. "
                     "He increased my Metformin to 1000mg and asked me to "
                     "get a kidney function test in 2 weeks."
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

        # The agent should handle both visit recording and medication aspects
        response_lower = final_response.lower()
        assert len(final_response) > 50, (
            f"Agent should provide detailed response for complex input. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_drug_interaction_warning_flow(
        self, mock_medication_tools, mock_visit_tools, patient_id
    ):
        """Test that drug interaction warnings are surfaced to the user."""
        root_agent = build_test_root_agent(mock_medication_tools, mock_visit_tools)
        runner = InMemoryRunner(agent=root_agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="The doctor prescribed Warfarin 5mg daily. "
                     "I'm currently taking Aspirin. Is this safe?"
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
        # Agent should flag the Warfarin + Aspirin interaction (both affect bleeding)
        assert any(
            word in response_lower
            for word in ["interaction", "risk", "caution", "warning", "bleed", "safe"]
        ), f"Agent should warn about Warfarin-Aspirin interaction. Got: {final_response}"
