"""Ask the boating-safety assistant a few questions, then score it on a dataset."""

import os

PROJECT_NAME = "langgraph-boating-safety-rag"
# Set before importing opik so every trace, dataset and experiment lands in this project.
os.environ.setdefault("OPIK_PROJECT_NAME", PROJECT_NAME)

import dotenv
import opik

dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))  # OPENAI_API_KEY

from boating_rag.evaluation import run_experiment
from boating_rag.graph import build_graph

QUESTIONS = [
    "Do children have to wear a life jacket in the cabin?",
    "Two powerboats are crossing paths. Who gives way?",
    "What should I say on the radio if someone falls overboard and is in danger?",
    "Do I need a licence to hunt waterfowl from my boat?",  # not in the handbook
]


def main() -> None:
    app = build_graph()

    # 1. Ask a few questions: each one is a trace in Opik.
    for question in QUESTIONS:
        result = app.invoke({"question": question})
        print(f"Q: {question}\nA: {result['answer']}\n")

    # 2. Score the same graph on the dataset: one experiment in Opik.
    evaluation = run_experiment(app)
    scores = evaluation.aggregate_evaluation_scores().aggregated_scores
    print(f"Experiment scores (mean over {len(evaluation.test_results)} questions):")
    for name, stats in scores.items():
        print(f"  {name}: {stats.mean:.2f}")
    if evaluation.experiment_url:
        print(f"\nExperiment: {evaluation.experiment_url}")

    # Traces are sent from a background thread; flush so none are lost on exit.
    opik.flush_tracker()


if __name__ == "__main__":
    main()
