"""The Opik test suite: assertions that catch invented values in extracted records."""

from typing import Any

import opik

from .agent import MODEL, intake_note
from .notes import NOTES
from .tracing import PROJECT_NAME, flush, traced

SUITE_NAME = PROJECT_NAME
traced_intake = traced(intake_note)

# Rules every record must follow, judged by an LLM against the note and the output.
GLOBAL_ASSERTIONS = [
    "Every non-null value in the record is stated in, or directly readable from, the desk note",
    "No color, brand, name or contact is invented: anything the note does not state is null",
    "If finder_contact is not null it is a phone number, extension or email address that appears in the note",
    "The item_type names the physical object the note is about",
]

# Item data holds ONLY the note the agent sees; expectations live in the assertions,
# otherwise the judge could read the answers instead of checking the output.
_EXPECTATIONS = [
    [
        "The item is an umbrella and its color is black",
        "The brand is null because the usher saw no brand",
        "The finder is Pia and the contact is pia.k@marlowehall.example",
    ],
    [
        "The item is a scarf, navy, with an embroidered fox as the distinguishing mark",
        "The finder is Bram and the contact is x4417",
    ],
    [
        "The item is a ring and the engraving 'M + J 2019' is recorded as a distinguishing mark",
        "finder_name and finder_contact are null because the writer did not note who handed it in",
    ],
    [
        "The item is a phone with a cracked screen and a golden retriever lock screen",
        "The brand is null: the note says 'iPhone' but never names Apple, and the color is null",
    ],
    [
        "The item is a backpack, green, and the brand is Fjallraven (accent optional)",
        "The finder is Sasha and the contact is 555-0188",
    ],
    [
        "The item is glasses with tortoiseshell frames",
        "finder_name is null: 'night shift' describes a work shift, not a person",
        "found_where and found_when are null because the note gives neither",
    ],
]

TEST_ITEMS = [{"data": {"note": n}, "assertions": a} for n, a in zip(NOTES, _EXPECTATIONS, strict=True)]


def run_suite() -> int:
    """Build the suite (idempotent) and run every note through the traced agent."""
    client = opik.Opik()
    # A test suite stores items plus plain-language assertions. runs_per_item=3 with a
    # pass_threshold of 2 lets the judge's and the model's run-to-run noise average out.
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy={"runs_per_item": 3, "pass_threshold": 2},
    )
    suite.insert(TEST_ITEMS)  # identical items are deduplicated on re-runs

    def task(item: dict[str, Any]) -> dict[str, Any]:
        # The traced call makes each run a trace in the project, linked to the experiment.
        return {"input": item, "output": traced_intake(item["note"])}

    # run_tests runs the task per item and has an LLM judge score every assertion;
    # the result is an experiment with a pass/fail per item (under Test Suites in Opik).
    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name=f"intake-{MODEL.split(':')[-1]}",
        worker_threads=4,
        generate_report=False,
    )
    print(f"\nPass rate: {result.pass_rate:.0%} ({result.items_passed}/{result.items_total} items)")
    for item_result in result.item_results.values():
        note = item_result.test_results[0].test_case.task_output["input"]["note"]
        print(f"  [{'PASS' if item_result.passed else 'FAIL'}] {note[:64]!r}...")
    print(f"\nExperiment: {result.experiment_name} ({result.experiment_url})")
    flush()
    return 0
