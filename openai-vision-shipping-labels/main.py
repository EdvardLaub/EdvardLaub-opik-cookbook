"""Draw eight shipping labels, extract typed fields from each with GPT-4o-mini
vision, print a per-field scoreboard, then grade the same labels with an Opik
test suite whose assertions carry the expected values."""

from typing import Any

import opik

from extractor import HERE, MODEL, PROJECT_NAME, extract_label
from labels import LABELS, render_all
from scoring import FIELDS, score_extraction
from suite import EXECUTION_POLICY, GLOBAL_ASSERTIONS, SUITE_NAME, build_items


def main() -> None:
    paths = render_all()  # labels/*.png, redrawn from labels.py every run
    print(f"Extracting fields from {len(LABELS)} labels with {MODEL}...\n")
    totals = dict.fromkeys(FIELDS, 0)
    for spec in LABELS:
        got = extract_label(str(paths[spec["id"]]))
        scores = score_extraction(spec, got)
        for field, ok in scores.items():
            totals[field] += ok
        misses = [f for f, ok in scores.items() if not ok]
        tag = spec["defect"] or "clean"
        print(f"  {spec['id']:<22} [{tag:<11}] {'all fields ok' if not misses else 'wrong: ' + ', '.join(misses)}")
    print("\nField accuracy:")
    for field in FIELDS:
        print(f"  {field:<16} {totals[field]}/{len(LABELS)}")

    # A test suite is a dataset whose items carry plain-language assertions.
    # get_or_create reuses it across runs; inserting identical items is a no-op.
    client = opik.Opik()
    suite = client.get_or_create_test_suite(
        name=SUITE_NAME,
        project_name=PROJECT_NAME,
        global_assertions=GLOBAL_ASSERTIONS,
        global_execution_policy=EXECUTION_POLICY,
    )
    suite.insert(build_items())

    def task(item: dict[str, Any]) -> dict[str, Any]:
        return {"input": item, "output": extract_label(str(HERE / item["image"]))}

    # run_tests runs the task per item (3x, per the execution policy), has an
    # LLM judge grade every assertion, and records an experiment with the
    # pass/fail results; each extraction is also a trace in the project.
    result = opik.run_tests(
        test_suite=suite,
        task=task,
        experiment_name="shipping-labels-gpt-4o-mini",
        worker_threads=3,
        generate_report=False,
    )
    print(f"\nSuite pass rate: {result.pass_rate:.0%} ({result.items_passed}/{result.items_total} labels)")
    for item_result in result.item_results.values():
        image = item_result.test_results[0].test_case.task_output["input"]["image"]
        print(f"  [{'PASS' if item_result.passed else 'FAIL'}] {image}")
    print(f"\nExperiment: {result.experiment_name} ({result.experiment_url})")

    # Traces and attachments upload in the background; flush before exiting
    # or the last ones can be lost.
    opik.flush_tracker()
    client.flush()


if __name__ == "__main__":
    main()
