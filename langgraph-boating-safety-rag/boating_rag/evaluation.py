"""Eval: a question dataset in Opik and an experiment scored by two LLM judges."""

import os

import opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import ContextPrecision, Hallucination

DATASET_NAME = "boating-safety-questions"
JUDGE_MODEL = "gpt-4o-mini"

DATASET_ITEMS = [
    {"question": "Do children have to wear a life jacket in the cabin?",
     "expected_output": "Yes. Anyone under 13 must wear a properly fitted life jacket "
                        "at all times while the vessel is underway, including in the cabin."},
    {"question": "How many life jackets must a boat carry?",
     "expected_output": "One wearable life jacket per person aboard, within reach and "
                        "sized for the wearer; boats over 12 metres also need a throwable device."},
    {"question": "Two powerboats are crossing paths. Who gives way?",
     "expected_output": "The vessel that has the other on its starboard side gives way; "
                        "the other vessel is the stand-on vessel and holds course and speed."},
    {"question": "What is the speed limit inside a harbor?",
     "expected_output": "5 knots, with no wake within 60 metres of docks, moored boats or swimmers."},
    {"question": "At what wind speed is a small craft advisory issued?",
     "expected_output": "When sustained winds of 18 to 33 knots or waves above 1.2 metres are expected."},
    {"question": "Which VHF channel do I use for a Mayday call?",
     "expected_output": "Channel 16, saying 'Mayday' three times followed by vessel name, "
                        "position, the emergency and the number of people aboard."},
    {"question": "How long should I run the bilge blower after fueling?",
     "expected_output": "At least 4 minutes before starting the engine."},
    # The handbook says nothing about this: the right answer is "I don't know".
    {"question": "Do I need a licence to hunt waterfowl from my boat?",
     "expected_output": "The handbook does not cover this; the assistant should say it doesn't know."},
]


def make_task(app):
    """Wrap the graph as an evaluation task returning what the judges need."""
    def rag_task(item: dict) -> dict:
        result = app.invoke({"question": item["question"]})
        return {"output": result["answer"], "context": result["context"]}
    return rag_task


def run_experiment(app, top_k: int | None = None):
    """Create/refresh the dataset and score the graph with Hallucination + ContextPrecision."""
    top_k = top_k or int(os.getenv("RAG_TOP_K", "3"))
    # get_or_create_dataset + insert: items show up in the Datasets tab and the
    # insert deduplicates, so re-running does not duplicate rows.
    dataset = opik.Opik().get_or_create_dataset(name=DATASET_NAME)
    dataset.insert(DATASET_ITEMS)

    # evaluate() runs the task per item and logs an experiment linked to the
    # dataset. Hallucination: 1.0 = answer not supported by the retrieved
    # context; ContextPrecision: 1.0 = retrieved context fits the question.
    return evaluate(
        dataset=dataset,
        task=make_task(app),
        scoring_metrics=[Hallucination(model=JUDGE_MODEL), ContextPrecision(model=JUDGE_MODEL)],
        # Metrics expect `input`; our dataset column is `question`.
        scoring_key_mapping={"input": "question"},
        experiment_name=f"rag-top{top_k}",
        experiment_config={"top_k": top_k, "model": "gpt-4o-mini"},
        task_threads=4,
    )
