# openai-vision-shipping-labels

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/openai-gpt--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Pillow](https://img.shields.io/badge/pillow-12%2B-3B77A8?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.100%2B-2f54eb?style=flat)

**A vision model reads parcel labels, and Opik keeps the label next to the answer, so you can see which smudge cost you a digit.**

When a model reads text out of an image and gets one character wrong, the trace
alone cannot tell you whether the model is sloppy or the image was
unreadable. This example extracts typed fields from shipping labels with
`gpt-4o-mini`, attaches every label PNG to its trace, and grades the results
with an Opik test suite. Four of the eight labels are deliberately bad, and
the suite is allowed to fail on them: in the run described below it passes
6 of 8 labels, and the two failures are the ones you would expect.

## What you'll build

- `labels.py` draws eight fictional labels with Pillow every time the app runs
  (UPS, FedEx, USPS and DHL layouts; nothing is committed as an image). Four
  are clean. Four are hard: a label **rotated about 13 degrees and sheared**
  on a dark tabletop, a FedEx label with a **thumb-smudge blurred over the
  tracking number**, a USPS label whose printed weight is **struck through
  with a handwritten correction** (`2.0 LB` crossed out, `3.5 lb` written
  beside it), and a DHL label degraded into a **low-resolution, noisy,
  tilted scan**.
- `extractor.py` sends each PNG to `gpt-4o-mini` with a strict JSON schema:
  carrier, tracking number, service level, ship date, weight (value and unit),
  and sender and recipient addresses split into name, street, city, region,
  postal code and country.
- `scoring.py` compares an extraction to the ground truth field by field
  (tracking numbers ignore spacing, weights convert units, addresses fold
  case, accents and ß), so the console prints a scoreboard.
- `suite.py` turns the same ground truth into an Opik test suite. Each label
  gets four plain-language assertions (carrier/service/date, tracking number,
  weight, addresses) and an LLM judge grades them. Each label runs three
  times and has to pass at least twice.

## See it in Opik

Open the **openai-vision-shipping-labels** project. It holds 32 traces: the 8
from the scoreboard pass, plus 24 from the suite (8 labels x 3 runs). Every
one has one attachment, an `image/png`, in the trace's Attachments panel;
open it and you see the label exactly as the model did. In the clean-label
traces the tree is `extract_label` (general) with a `chat_completion_create`
llm span inside it, model `gpt-4o-mini-2024-07-18`. Image input is not cheap:
the extraction spans average about 24,600 tokens, roughly $0.002 each, and
all 32 together cost about $0.06. Suite traces add a `task` span and the
judge's `llm_judge` spans, which is where the 24 extra llm spans come from.

The traces carry `label_id` in their metadata (`06_fedex_smudged`, ...), so
filter or search on it to line up the four runs of one label. Compare them:

- **06_fedex_smudged**: the real tracking number is `7712 4086 9351`. The
  four extractions read `7712 4664 3811`, `7712 468 301 0`, `7712 4963 2010`
  and `7712 4683 2951`: the first four digits survive and everything under
  the smudge is invented, differently on every run. A different guess each
  time is the sign that the model is not reading anything.
- **08_dhl_lowres**: the ship date comes back as `2020-03-11` instead of
  `2026-03-11` on all four runs, and the sender name is a different
  hallucination each time (`Handel Cebas`, `Handelgesellschaft`,
  `Handels Oebels`, `Handelt Optics` for `Nordlicht Optics`), once with the
  street misread as `Kaisermühlen 8`. Weight, tracking number and recipient
  came through.
- **07_usps_handwritten** passes: all four runs return `3.5 lb`, the
  handwriting, not the crossed-out `2.0`. **05_ups_skewed** passes as well:
  all seven scored fields were right on every run.

Open **Test suites** and pick `openai-vision-shipping-labels`, then the
`shipping-labels-gpt-4o-mini` experiment. Pass rate 75% (6/8 labels). The
smudged label fails its tracking-number assertion on 0 of 3 runs, and the
low-res label fails the date and address assertions on 0 of 3 runs. The
three global assertions pass 24/24. The local scoreboard from the same run
agrees: tracking number 7/8, ship date 7/8, sender 7/8, everything else 8/8.
Judged runs vary a little, so your numbers may differ.

## Run it yourself

1. Have a local Opik running (workspace `default`) and `~/.opik.config`
   pointing at it, or run `opik configure`.
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a `.env` one directory up
   also works).
3. `uv sync`
4. `uv run main.py` (about 2 minutes; the suite is the slow part)
5. Open the project in Opik as described above. The console prints the
   experiment link at the end.

To run only the offline tests: `uv run pytest`.

## Poke around

- Turn the smudge into a stronger or weaker one: change the blur radius `5.5`
  in `_smudge` in `labels.py` and see at what radius `tracking_number` flips
  from invented to correct.
- Change `"detail": "high"` to `"low"` in `extractor.py`. Tokens per call
  drop sharply; the suite shows which fields pay for it.
- Add a ninth label to `LABELS` with a defect of your own (a torn corner,
  a second handwritten correction). Its assertions are generated for you.
- Check the attachments from code. This needs the project id and the base64
  of the Opik API URL:

  ```python
  import base64, opik
  c = opik.Opik()
  pid = c.rest_client.projects.retrieve_project(name="openai-vision-shipping-labels").id
  path = base64.b64encode(b"http://localhost:5173/api/").decode()
  trace = c.search_traces(project_name="openai-vision-shipping-labels", max_results=1)[0]
  print(c.rest_client.attachments.attachment_list(
      project_id=pid, entity_type="trace", entity_id=trace.id, path=path).content)
  ```

## Gotchas we hit

- **Suite traces have a different output shape.** Symptom: scoring the
  `output` of the suite's traces gives 0 of 7 fields right even though the
  extraction was fine. Cause: the suite task returns
  `{"input": item, "output": extract_label(...)}`, so the trace output is the
  wrapper. Fix: read `trace.output["output"]` for suite traces; the first 8
  traces hold the bare fields.
- **Re-running piles up traces and experiments.** Symptom: twice as many traces after a
  second run, and two experiments named `shipping-labels-gpt-4o-mini`. Cause:
  every run traces again and `run_tests` creates a new experiment each time
  (the suite and its items are reused). Fix: delete the old traces
  (`POST /api/v1/private/traces/delete` with their ids) and old experiment
  before a run you want to count.
- **A fair scorer matters as much as a fair model.** Symptom: `sender` was
  reported wrong on the low-res label even where the model returned
  `Kaiserstraße 8` for `Kaiserstrasse 8`. Cause: stripping punctuation does not
  make `ß` equal `ss`. Fix: `norm_text` in `scoring.py` does
  `value.casefold().replace("ß", "ss")` and NFKD-folds accents. The sender
  still fails on that label, honestly, because the name is hallucinated.
- **Pydantic serializer warnings during the suite.** Symptom: several
  `PydanticSerializationUnexpectedValue ... Expected Message` warnings printed
  while `run_tests` runs. Cause: the judge's LiteLLM response is re-serialized
  by Pydantic. They are noise: scores and traces are recorded normally.

## How it's put together

- `labels.py`: ground truth for the eight labels and the Pillow code that draws them and their defects.
- `extractor.py`: the vision call, the JSON schema, `track_openai`, `@opik.track` and the trace attachment.
- `scoring.py`: offline field-by-field comparison with normalization.
- `suite.py`: assertions generated from the ground truth, the execution policy (3 runs, 2 must pass).
- `main.py`: draws the labels, prints the scoreboard, runs the suite, flushes.
- `tests/`: offline tests (scoring, assertions, rendering, and a traced call with a stubbed client and tracking disabled). Run with `uv run pytest`; they need no keys.
- `.env.example`: the one key needed.

---

*built with Opik · inspired by Opik's examples and documentation*
