"""Agent factory: a CodeAgent that may use pandas and nothing else beyond smolagents' safe defaults."""

from smolagents import CodeAgent, OpenAIServerModel

MODEL_ID = "gpt-4o-mini"


def build_agent(max_steps: int = 6) -> CodeAgent:
    # A CodeAgent answers by writing Python and running it in smolagents' local executor;
    # only the imports listed here (plus the safe defaults) are allowed.
    return CodeAgent(
        tools=[],
        model=OpenAIServerModel(model_id=MODEL_ID),
        additional_authorized_imports=["pandas"],
        max_steps=max_steps,
    )
