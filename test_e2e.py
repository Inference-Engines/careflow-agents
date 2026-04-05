"""End-to-end smoke test for the CareFlow root agent.

Runs one Runner invocation per representative user scenario and prints which
sub-agents got called, so we can verify Boss -> sub_agent transfer is actually
firing after the factory refactor. Keep this file out of pytest; it hits live
Vertex AI and rate-limits easily.
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from pathlib import Path

# Windows 콘솔에서 UTF-8 출력 강제 — 이모지/한글 에이전트 응답이 cp949로 깨지는 것 방지.
# Force UTF-8 on Windows consoles so Korean / emoji output from agents doesn't blow up.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 로컬 .env 로드 (python-dotenv 없이 최소 구현).
# Minimal .env loader so this script stays dependency-light.
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from careflow.agent import root_agent


# 아래 시나리오 목록은 설계 문서의 9개 intent와 1:1 매핑.
# These scenarios mirror the 9 intents from the design doc, one per intent.
SCENARIOS: list[tuple[str, str]] = [
    ("POST_VISIT",   "I went to the doctor today. Dr. Patel changed my Metformin to 1000mg twice daily. Need HbA1c test in 2 weeks."),
    ("INSIGHT",      "How has my blood pressure been trending over the past 3 months?"),
    ("DIET",         "What can I eat for lunch? My doctor said reduce sodium."),
    ("SYMPTOM_MED",  "I am feeling dizzy and my hands are shaking."),
    ("SYMPTOM_HIGH", "I have severe chest pain and difficulty breathing."),
    ("ADHERENCE",    "Did I take my medications today?"),
    ("SCHEDULE",     "When is my next appointment?"),
    ("CAREGIVER",    "I am Priya, Rajesh's daughter. How has my father been doing this week?"),
    ("OFF_TOPIC",    "What is bitcoin price today?"),
]


async def _run_one(runner: Runner, user_id: str, session_id: str, message: str) -> None:
    """Run a single scenario and print the agent trace + final text."""
    content = types.Content(role="user", parts=[types.Part(text=message)])
    agent_trace: list[str] = []
    final_text = ""

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # event.author == 에이전트 이름. 중복 방지는 아래에서 dict.fromkeys 로.
            # event.author is the agent name; we dedupe later while preserving order.
            if getattr(event, "author", None):
                agent_trace.append(event.author)

            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text = part.text
    except Exception as exc:  # 데모 스모크 테스트이므로 개별 시나리오 실패가 전체를 멈추면 안 됨.
        # Smoke test: a single scenario failing must not kill the batch.
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        traceback.print_exc(limit=3)
        return

    unique_agents = list(dict.fromkeys(agent_trace))
    print(f"[AGENTS]   {' -> '.join(unique_agents) or '(none)'}")
    # 응답은 200자로 잘라 한 줄 요약 — 전체 응답이 필요하면 ADK web UI 사용.
    # Truncate to 200 chars; full response is available via the ADK web UI.
    print(f"[RESPONSE] {final_text[:200].replace(chr(10), ' ')}")


async def main() -> None:
    app_name = "careflow_e2e"
    user_id = "patient_rajesh"
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
    )

    for idx, (label, message) in enumerate(SCENARIOS):
        session_id = f"session_{idx}"
        await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        print("\n" + "=" * 70)
        print(f"[{label}] {message}")
        print("=" * 70)
        await _run_one(runner, user_id, session_id, message)
        # Flash 는 1000 RPM 이라 3초면 충분. Pro 로 돌릴 땐 13초로 늘릴 것.
        # Flash handles 1000 RPM, so 3s is enough. Bump to 13s when using Pro.
        if idx < len(SCENARIOS) - 1:
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
