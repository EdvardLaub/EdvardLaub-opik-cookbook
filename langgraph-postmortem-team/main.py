"""Draft a blameless post-mortem for the fictional Brightloom payments outage."""

import pathlib

import dotenv
from langchain_openai import ChatOpenAI

from postmortem.team import build_graph

# Secrets live in the repo-root .env (OPENAI_API_KEY).
dotenv.load_dotenv(pathlib.Path(__file__).parents[1] / ".env")

INCIDENT = (
    "On 2026-10-02 Brightloom's payments API (ledger-api) failed for most checkouts. "
    "Write the blameless post-mortem for this incident."
)


def main() -> None:
    app = build_graph(ChatOpenAI(model="gpt-4o-mini", temperature=0)).compile()
    result = app.invoke({"incident": INCIDENT})

    print("Evidence questions:")
    for i, q in enumerate(result["questions"], 1):
        print(f"  {i}. {q}")
    print("\n" + result["postmortem"])


if __name__ == "__main__":
    main()
