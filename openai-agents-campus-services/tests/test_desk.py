"""Offline tests: no keys, no model calls, Opik tracking disabled."""

import asyncio
import json

import pytest
from agents import trace
from agents.tool_context import ToolContext

import desk_data as db
import main


def test_housing_assignment_and_unhoused_student():
    assert db.housing_assignment("S1001")["hall"] == "Kelp Hall"
    assert db.housing_assignment("S1004")["assignment"] is None
    assert "error" in db.housing_assignment("S9999")


def test_vacancy_filters():
    rooms = db.housing_vacancies(800, "single")["vacancies"]
    assert {r["room"] for r in rooms} == {"301"}
    assert "error" in db.housing_vacancies(100)


def test_room_change_only_into_vacant_rooms():
    ok = db.room_change_request("S1001", "kelp hall", "301")
    assert ok["status"] == "submitted" and ok["ticket"].startswith("HSG-")
    assert "error" in db.room_change_request("S1001", "Kelp Hall", "214")


def test_aid_totals():
    pkg = db.aid_package("S1001")
    assert pkg["total_offered"] == 13800 and pkg["free_money"] == 8500
    assert db.aid_tasks("S1002")["tasks"][0]["status"] == "missing"


def test_registrar_credits_and_holds():
    assert db.class_schedule("S1001")["total_credits"] == 11
    assert db.account_holds("S1004")["holds"][0]["blocks"] == ["registration", "transcripts"]
    assert db.account_holds("S1001")["holds"] == []


def test_every_specialist_is_a_handoff_target():
    names = {a.name for a in main.triage_agent.handoffs}
    assert names == {"Housing Agent", "Financial Aid Agent", "Registrar Agent"}


def test_function_tool_runs_with_tracing_installed_but_disabled():
    # The Opik processor is registered, yet the tool still runs and returns data
    # inside a trace() block when OPIK_TRACK_DISABLE=true.
    main.setup_tracing()
    args = json.dumps({"student_id": "S1003"})
    ctx = ToolContext(context=None, tool_name="get_aid_package",
                      tool_call_id="call_1", tool_arguments=args)
    with trace(workflow_name="test", group_id="test-thread"):
        out = asyncio.run(main.get_aid_package.on_invoke_tool(ctx, args))
    assert json.loads(out)["scholarship"] == 4000
