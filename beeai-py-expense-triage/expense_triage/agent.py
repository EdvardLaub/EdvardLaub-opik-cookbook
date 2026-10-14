"""The triage agent: a BeeAI ReAct agent on gpt-4o-mini with three tools.

Every report gets a fresh agent and memory, so one report is one independent run.
"""

import re

from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel, ChatModelParameters
from beeai_framework.memory import UnconstrainedMemory

from expense_triage import data
from expense_triage.tools import TOOLS

MODEL = "openai:gpt-4o-mini"

INSTRUCTIONS = f"""You are the first-pass expense reviewer at Fernwood Outfitters.
For each expense report, decide exactly one of: {", ".join(data.DECISIONS)}.

Work like this:
1. Call lookup_expense_policy for the report's category.
2. For meals and lodging, call check_per_diem with the city, amount and number of days.
3. Call get_prior_claims for the employee and look for a duplicate (same date, amount and description).
Never state a limit, threshold or prior claim you did not get from a tool.

Decision rules, in this order:
- escalate: over the per-diem, a duplicate of a prior claim, or over the category's pre-approval limit.
- needs-receipt: not escalated, but a receipt is required (amount over the receipt threshold, or the policy says always) and the report says it is not attached.
- approve: everything else.

Your final answer must be exactly two lines:
Decision: <approve | needs-receipt | escalate>
Reason: <one sentence citing the tool results>"""


def build_agent() -> ReActAgent:
    llm = ChatModel.from_name(MODEL, ChatModelParameters(temperature=0))
    return ReActAgent(
        llm=llm,
        tools=TOOLS,
        memory=UnconstrainedMemory(),
        # The company-specific instructions go into the ReAct system prompt template.
        templates={
            "system": lambda tpl: tpl.fork(
                lambda cfg: cfg.model_copy(update={"defaults": {**cfg.defaults, "instructions": INSTRUCTIONS}})
            )
        },
    )


def parse_decision(text: str) -> str | None:
    """Pull the decision out of the agent's final answer; None if it didn't follow the format."""
    m = re.search(r"Decision:\s*\**\s*(approve|needs-receipt|escalate)\b", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


async def triage_report(report: dict) -> tuple[str | None, str]:
    """Run the agent on one report; returns (decision, full final text)."""
    agent = build_agent()
    # BeeAI Python takes the prompt positionally (not prompt=...) and the limits as keyword args.
    response = await agent.run(
        data.format_report(report), max_iterations=8, max_retries_per_step=3, total_max_retries=10
    )
    text = response.last_message.text  # Python: no .result (TS-style docs); the answer is the last output message
    return parse_decision(text), text


