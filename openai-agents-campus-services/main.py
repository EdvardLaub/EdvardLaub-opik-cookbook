"""Student-services desk on the OpenAI Agents SDK, traced with Opik.

A triage agent hands off to housing, financial-aid or registrar specialists.
Each specialist owns tools that read the fictional records in data/. Opik's
OpenAI Agents integration turns every run into a trace: agent spans, handoff
spans, tool spans with arguments and results, and llm spans with token usage.
Each scripted conversation shares a group_id, which Opik shows as a thread.
"""

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (if present) and pin the Opik project name
# BEFORE opik is imported, so every trace lands in this project.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ.setdefault("OPIK_PROJECT_NAME", "openai-agents-campus-services")

import opik
from agents import Agent, Runner, function_tool, set_trace_processors, trace
from opik.integrations.openai.agents import OpikTracingProcessor

import desk_data as db

MODEL = "gpt-4o-mini"


def setup_tracing() -> None:
    # OpikTracingProcessor replaces the SDK's default exporter: agent runs become
    # traces, handoffs and function tools become spans, model calls become llm spans.
    set_trace_processors(processors=[OpikTracingProcessor()])


# ---------------------------------------------------------------------------
# Tools. Each @function_tool shows up in Opik as a `tool` span whose input is
# the arguments the model chose and whose output is the JSON we return.
# ---------------------------------------------------------------------------

@function_tool
def get_housing_assignment(student_id: str) -> str:
    """Look up where a student currently lives (hall, room, lease end)."""
    return json.dumps(db.housing_assignment(student_id))


@function_tool
def find_vacancies(max_rent_per_month: float, room_type: str = "") -> str:
    """List vacant rooms at or under a monthly rent. room_type: single, double or studio (optional)."""
    return json.dumps(db.housing_vacancies(max_rent_per_month, room_type))


@function_tool
def request_room_change(student_id: str, hall: str, room: str) -> str:
    """Submit a room-change request for a student into a vacant room; returns a ticket id."""
    return json.dumps(db.room_change_request(student_id, hall, room))


@function_tool
def get_aid_package(student_id: str) -> str:
    """Return a student's 2026-27 aid offer: grant, scholarship, loan, work-study and totals."""
    return json.dumps(db.aid_package(student_id))


@function_tool
def get_aid_tasks(student_id: str) -> str:
    """Return outstanding financial-aid to-dos for a student, plus global aid deadlines."""
    return json.dumps(db.aid_tasks(student_id))


@function_tool
def get_class_schedule(student_id: str) -> str:
    """Return a student's current-term courses and total credits."""
    return json.dumps(db.class_schedule(student_id))


@function_tool
def get_account_holds(student_id: str) -> str:
    """Return registration/transcript holds on a student, plus add/drop and withdrawal deadlines."""
    return json.dumps(db.account_holds(student_id))


# ---------------------------------------------------------------------------
# Agents: one triage agent and three specialists it can hand off to.
# ---------------------------------------------------------------------------

STYLE = "Students give you their id (like S1001). Use your tools for facts; never guess. Keep replies under 80 words."

housing_agent = Agent(
    name="Housing Agent",
    handoff_description="Room assignments, vacancies and room-change requests.",
    instructions=f"You are the housing specialist at Larkspur University. {STYLE}",
    model=MODEL,
    tools=[get_housing_assignment, find_vacancies, request_room_change],
)

aid_agent = Agent(
    name="Financial Aid Agent",
    handoff_description="Aid offers, grants, loans, work-study and aid paperwork.",
    instructions=f"You are the financial-aid specialist at Larkspur University. {STYLE}",
    model=MODEL,
    tools=[get_aid_package, get_aid_tasks],
)

registrar_agent = Agent(
    name="Registrar Agent",
    handoff_description="Class schedules, credits, registration holds and academic deadlines.",
    instructions=f"You are the registrar specialist at Larkspur University. {STYLE}",
    model=MODEL,
    tools=[get_class_schedule, get_account_holds],
)

# handoffs=[...] makes each specialist a transfer target; every transfer is
# recorded as a `Handoff` span so a misrouted request is visible in the tree.
triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are the front desk of the Larkspur University student-services desk. "
        "Never answer questions yourself. Hand off to housing, financial aid or the "
        "registrar. If a message needs several, start with the one the student "
        "asked about first."
    ),
    model=MODEL,
    handoffs=[housing_agent, aid_agent, registrar_agent],
)


# ---------------------------------------------------------------------------
# Demo: scripted multi-turn conversations; no human input.
# ---------------------------------------------------------------------------

DEMO_CONVERSATIONS = {
    # Turn 2 asks for housing AND registrar help; the specialists can't hand off
    # to each other, so the credit question goes unanswered (visible in the trace).
    "maren-move": [
        "Hi, I'm S1001. Where do I live right now, and is there a single under $800 open?",
        "Please request the Kelp Hall single for me. Then, am I carrying enough credits this term?",
    ],
    # Turn 1 goes to Financial Aid; turn 2 is re-triaged and lands on the Registrar.
    "tobias-paperwork": [
        "S1002 here. What's my aid package for this year?",
        "What do I still need to submit, and do I have any holds blocking registration?",
    ],
    # Single-turn thread asking for two departments at once: only one is answered.
    "declan-appeal": [
        "I'm S1004. Why can't I register, and what's my financial-aid status?",
    ],
}


def run_demo() -> None:
    for conversation_id, user_turns in DEMO_CONVERSATIONS.items():
        thread_id = f"{conversation_id}-{uuid.uuid4().hex[:8]}"
        print(f"\n=== Conversation: {conversation_id} (thread {thread_id}) ===")
        history: list = []
        for user_message in user_turns:
            print(f"\nStudent: {user_message}")
            history.append({"role": "user", "content": user_message})
            # One trace per turn. The shared group_id is what Opik uses as the
            # thread id, so the Threads tab stitches these turns together.
            with trace(workflow_name="Student services desk", group_id=thread_id):
                result = Runner.run_sync(triage_agent, history)
            print(f"{result.last_agent.name}: {result.final_output}")
            history = result.to_input_list()


if __name__ == "__main__":
    setup_tracing()
    try:
        run_demo()
    finally:
        # Traces are sent in a background thread; flushing stops the process
        # from exiting before the last spans reach Opik.
        opik.flush_tracker()
