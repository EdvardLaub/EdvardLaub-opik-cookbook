# openai-agents-campus-services

*A student-services desk where one question can bounce through three departments, and the trace shows every hop.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![openai-agents](https://img.shields.io/badge/openai--agents-0.23.1-412991?style=flat)
![Opik](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)

A student writes "Why can't I register, and what's my aid status?" and gets back half an answer. Was it the front desk routing to the wrong office? A specialist that had no tool for the second half? A tool that returned the wrong row? From the reply alone you can't tell. This example is a fictional university desk (Larkspur University) built so you can see exactly where each question went and what each office looked up.

## What you'll build

Four agents on `gpt-4o-mini`:

- a **Triage Agent** that never answers, only hands off;
- a **Housing Agent** (`get_housing_assignment`, `find_vacancies`, `request_room_change`);
- a **Financial Aid Agent** (`get_aid_package`, `get_aid_tasks`);
- a **Registrar Agent** (`get_class_schedule`, `get_account_holds`).

The tools read four small JSON files in `data/` (students, housing, aid, registrar), so there is no external service and no extra key. `desk_data.py` holds the lookups as plain functions; `main.py` wraps them as tools and wires the agents. Tracing is Opik's OpenAI Agents integration, one line: `set_trace_processors([OpikTracingProcessor()])`. The demo runs three scripted conversations (5 turns) and tags each with a `group_id` so Opik groups them into threads.

## See it in Opik

Open the **openai-agents-campus-services** project. After one run it holds **5 traces**, all named `Student services desk`, each with 11 or 12 spans (about 1,000 tokens per turn, roughly $0.0003 per turn on `gpt-4o-mini`).

Click the first trace. The tree reads `Task` > `Triage Agent` (one `Turn`/`Response` pair, its llm span) > `Handoff` > `Housing Agent` > `Turn`/`Response` > two `tool` spans, `get_housing_assignment` and `find_vacancies`, > a final `Turn`/`Response` that writes the reply. Open a tool span: its input is the exact arguments the model chose (`{"student_id": "S1001"}`) and its output is the JSON from `data/`, here the Kelp Hall 214 assignment and the $780 single in room 301. The `Handoff` span is where routing is decided; the three `Response` spans are `llm` spans with token usage and estimated cost.

Now open the **Threads** tab. There are **3 threads**, named like `maren-move-f32ba42e` (the suffix changes each run). The `maren-move` thread has two traces. In its second turn the student asks for a room change and a credit check. The trace shows `request_room_change` firing and a ticket coming back, but no registrar span: the Housing Agent has no way to hand the conversation on, so it asks the student for their credit load instead of looking it up. In `declan-appeal`, one message asks about registration and aid; the Registrar Agent finds the unpaid-tuition hold and tells the student to ask the aid office, and no Financial Aid span ever appears. Those are the failures a multi-agent desk produces, and they are visible only in the tree.

## Run it yourself

1. Install [uv](https://docs.astral.sh/uv/) and have a local Opik running (or set `OPIK_API_KEY` and `OPIK_WORKSPACE` for Comet cloud).
2. `cd openai-agents-campus-services`
3. `cp .env.example .env` and add `OPENAI_API_KEY` (a `.env` one directory up works too).
4. `uv sync`
5. `uv run main.py` (about 40 seconds).
6. Open the project in Opik: traces, then Threads.
7. Offline tests: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`

## Poke around

- Let specialists send students back: after the agents are defined, add `housing_agent.handoffs = [triage_agent]` (same for the other two) and rerun. The `maren-move` second turn should grow a second `Handoff` span.
- Make a tool lie: have `account_holds` return an empty list for `S1004` and see how the Registrar Agent explains the registration block. The tool span shows the empty data, the llm span shows the model smoothing over it.
- Ask for something no office owns ("Where is the library?") and watch whether the Triage Agent invents an answer or hands off anyway.
- Add a fourth specialist (campus parking, say) with one tool. No tracing change is needed; its handoff and tool spans appear on their own.

## Gotchas we hit

- **Handoffs are `general` spans, not their own type.** If you filter the span list by type looking for handoffs, you find none. Cause: the integration records a handoff as a `general` span named `Handoff`, and agent turns as `general` spans too; only function tools are `tool` and model calls `llm`. Fix: filter by name (`Handoff`) or read the tree.
- **Threads need `group_id` on every turn.** If each turn is its own row in the Threads tab (or the tab is empty), the turns were run without a shared `group_id` (it becomes the trace `thread_id`, which the run above confirmed). Fix: `with trace(workflow_name="Student services desk", group_id=thread_id): Runner.run_sync(...)`, with the same `thread_id` for every turn of a conversation.

## How it's put together

- `main.py` - tracing setup, tool wrappers, the four agents, and the scripted conversations with thread grouping.
- `desk_data.py` - plain-Python lookups over `data/`, with no agent or Opik code.
- `data/*.json` - fictional students, housing, financial-aid and registrar records.
- `tests/test_desk.py` - offline tests for the lookups, the handoff wiring, and one tool call run through the SDK with the Opik processor installed and tracking disabled.
- `pyproject.toml`, `.env.example`, `.gitignore` - dependencies (pinned) and config.

---

*built with Opik · inspired by Opik's examples and documentation*
