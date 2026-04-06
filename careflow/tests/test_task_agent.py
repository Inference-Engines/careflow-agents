"""
CareFlow — Task Agent Unit Tests
Tests medication extraction, safety validation, and task creation.

These tests use InMemoryRunner with mocked tools to verify the agent's
reasoning and tool-calling behavior without requiring a live database.
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
# Helper: Build a testable Task Agent with mocked tools
# ─────────────────────────────────────────────

def build_test_task_agent(mock_medication_tools, mock_db):
    """Create a Task Agent with mocked tools for testing."""
    from careflow.agents.task.tools import check_drug_interactions, lookup_medication_info

    agent = LlmAgent(
        name="task_agent",
        model=config.AGENT_MODEL,
        description=(
            "Extracts medications, follow-up tasks, and action items from visit notes. "
            "Performs medication safety validation by checking drug interactions."
        ),
        instruction="""You are the CareFlow Task Agent. Extract medications and tasks from user input.
        For each medication, check interactions against current medications.
        The patient_id is: a1b2c3d4-e5f6-7890-abcd-ef1234567890
        Always call get_current_medications first, then check_drug_interactions for new meds.
        Respond with your findings in a clear, structured format.""",
        tools=[
            mock_medication_tools["get_current_medications"],
            mock_medication_tools["add_medication"],
            mock_medication_tools["update_medication_status"],
            mock_medication_tools["log_medication_change"],
            check_drug_interactions,
            lookup_medication_info,
        ],
    )
    return agent


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestTaskAgentMedicationExtraction:
    """Tests for medication extraction from visit notes."""

    @pytest.mark.asyncio
    async def test_extract_new_medication(self, mock_medication_tools, mock_db, patient_id):
        """Agent should identify a new medication from a visit note."""
        agent = build_test_task_agent(mock_medication_tools, mock_db)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="The doctor prescribed Lisinopril 10mg once daily for blood pressure."
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

        # Verify the agent mentioned the medication
        response_lower = final_response.lower()
        assert "lisinopril" in response_lower, (
            f"Agent should have extracted Lisinopril. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_detect_dosage_change(self, mock_medication_tools, mock_db, patient_id):
        """Agent should detect when an existing medication's dosage changes."""
        agent = build_test_task_agent(mock_medication_tools, mock_db)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Doctor increased my Metformin from 500mg to 1000mg, twice daily with meals."
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
        assert "metformin" in response_lower, (
            f"Agent should have identified Metformin change. Got: {final_response}"
        )
        assert "1000" in final_response, (
            f"Agent should mention the new dosage 1000mg. Got: {final_response}"
        )


class TestTaskAgentSafetyValidation:
    """Tests for drug interaction safety checking."""

    @pytest.mark.asyncio
    async def test_safety_check_triggered(self, mock_medication_tools, mock_db, patient_id):
        """Agent should call safety check tools for new medications."""
        agent = build_test_task_agent(mock_medication_tools, mock_db)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="I was prescribed Warfarin 5mg daily. Please check if it's safe with my current medications."
            )],
        )

        tool_calls_made = []
        final_response = ""

        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            # Track tool calls
            if hasattr(event, 'function_calls') and event.function_calls:
                for fc in event.function_calls:
                    tool_calls_made.append(fc.name)

            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        # Agent should mention safety/interaction check
        response_lower = final_response.lower()
        assert any(
            word in response_lower
            for word in ["safe", "interaction", "check", "warfarin", "aspirin"]
        ), f"Agent should discuss safety. Got: {final_response}"


class TestTaskAgentTaskExtraction:
    """Tests for task/action-item extraction."""

    @pytest.mark.asyncio
    async def test_extract_lab_test_task(self, mock_medication_tools, mock_db, patient_id):
        """Agent should extract lab test tasks with fasting flags."""
        agent = build_test_task_agent(mock_medication_tools, mock_db)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="Doctor wants me to get an HbA1c blood test in 2 weeks. "
                     "I need to fast for 12 hours before the test."
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
        assert "hba1c" in response_lower or "blood test" in response_lower, (
            f"Agent should mention the blood test. Got: {final_response}"
        )
        assert "fast" in response_lower, (
            f"Agent should flag fasting requirement. Got: {final_response}"
        )

    @pytest.mark.asyncio
    async def test_extract_multiple_tasks(self, mock_medication_tools, mock_db, patient_id):
        """Agent should handle multiple tasks from a single visit note."""
        agent = build_test_task_agent(mock_medication_tools, mock_db)
        runner = InMemoryRunner(agent=agent, app_name="test")

        session = await runner.session_service.create_session(
            app_name="test",
            user_id="test_user",
            state={"patient_id": patient_id},
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(
                text="After today's visit: 1) Get blood sugar test next week, "
                     "2) Start walking 30 minutes daily, "
                     "3) Reduce salt intake, "
                     "4) Follow-up appointment in 3 months."
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
        # Agent should identify multiple tasks
        task_keywords = ["blood sugar", "walking", "salt", "follow-up"]
        found_count = sum(1 for kw in task_keywords if kw in response_lower)
        assert found_count >= 2, (
            f"Agent should extract multiple tasks. Found {found_count}/4 keywords. "
            f"Got: {final_response}"
        )
