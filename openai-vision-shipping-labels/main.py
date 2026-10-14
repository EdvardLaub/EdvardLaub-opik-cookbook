"""Draw eight shipping labels, extract typed fields from each with GPT-4o-mini
vision, and print a per-field scoreboard against the known ground truth."""

from extractor import MODEL, extract_label
from labels import LABELS, render_all
from scoring import FIELDS, score_extraction


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


if __name__ == "__main__":
    main()
