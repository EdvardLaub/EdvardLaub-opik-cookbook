"""The metric: did the model answer with exactly the right routing label?"""

from sightings import LABELS


def normalise(answer: str) -> str:
    """Lowercase, trim quotes/punctuation, and unify separators.

    Deliberately light-touch: "Birds." passes, "This is a bird sighting" does not.
    The output format is part of what the optimizer must learn.
    """
    cleaned = answer.strip().lower().strip(".!\"'` *")
    return cleaned.replace("-", "_").replace(" ", "_").replace("/", "_")


def label_accuracy(dataset_item: dict, llm_output: str) -> float:
    """1.0 when the normalised answer is the labelled group, else 0.0."""
    return 1.0 if normalise(llm_output) == dataset_item["label"] else 0.0


def is_valid_label(answer: str) -> bool:
    return normalise(answer) in LABELS
