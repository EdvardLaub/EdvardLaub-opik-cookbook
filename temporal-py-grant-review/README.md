# temporal-py-grant-review

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![temporalio](https://img.shields.io/badge/temporalio-1.34-000000?style=flat)
![Opik](https://img.shields.io/badge/opik-2.2.100-2f54eb?style=flat)

*One grant application, one Opik trace, two operating-system processes, and the retry that happened in between.*

A durable workflow is split by design. A client asks for a review and walks away; a worker, usually on another
machine, does the slow and flaky part. When something goes wrong at 3am you want a single page that shows the
request, the decision, the failed attempt and the model's reasoning, not two log streams to line up by timestamp.
This example builds a small version of that and gets Opik to draw it as one tree.

## What you'll build

Reviews for the (made-up) Larkfield Neighbourhood Foundation's community grants. Each application goes through a
Temporal workflow with three activities:

1. **check_eligibility** looks the applicant up in a stubbed charity register and applies the rules (registered,
   Larkfield postcode, at most GBP 5,000). The register "times out" on the first attempt of every call, so Temporal's
   retry policy has to rescue it.
2. **score_application** asks `gpt-4o-mini` to score community benefit, feasibility and value for money (1-5 each).
   Ten or more points out of fifteen approves.
3. **draft_letter** asks the model to write the decision letter.

Three applications run at once: an orchard project (approved, 13/15), a floodlight request with no quotes or
permissions (declined, 6/15) and a gallery that the register lists as dissolved (declined without scoring).

`python -m grantreview` is the client. It boots a local Temporal dev server, spawns `python -m grantreview.worker`
as a second process, and talks to it over gRPC. Both processes load `grantreview/tracing.py`, which installs an
OpenTelemetry exporter pointed at Opik and returns Temporal's `TracingInterceptor`. Temporal copies the trace context
into its own message headers, so spans the worker creates become children of spans the client created.

## See it in Opik

Open http://localhost:5173, project **temporal-py-grant-review**. There are three traces, `review:GR-2041`,
`review:GR-2042` and `review:GR-2043`, each with Input (the application) and Output (decision and letter) filled in.

Open `review:GR-2041` (13 spans, about 4.7 s, 559 tokens, roughly $0.00016). The tree is:

```
review:GR-2041                         client process
  StartWorkflow:GrantReviewWorkflow    client process
    StartActivity:check_eligibility
      RunActivity:check_eligibility    ERROR  Charity register timed out (503 from registry.example.org)
      RunActivity:check_eligibility    succeeds about a second later
    RunWorkflow:GrantReviewWorkflow    worker process
    StartActivity:score_application
      RunActivity:score_application
        score-application              llm span: prompt, JSON answer, 324 tokens
    StartActivity:draft_letter
      RunActivity:draft_letter
        draft-decision-letter          llm span: 235 tokens
    CompleteWorkflow:GrantReviewWorkflow
```

Everything below `StartWorkflow` was emitted by the worker, yet it hangs off a root the client opened: that is the
cross-process trace. The two `RunActivity:check_eligibility` spans are the retry; click the first and the error panel
shows the exception type, the message and the traceback. `GR-2043` (dissolved gallery) has 10 spans and a single llm
span, because it never reaches scoring. The two `llm` spans carry model `gpt-4o-mini`, provider `openai`, token usage
and an estimated cost; the rest are `general` spans.

`uv run python -m grantreview.verify` reads the project back through the SDK and prints these trees, checking each
trace has one root, worker spans under it, one failed and one successful eligibility attempt, and usage and
input/output on each llm span.

## Run it yourself

1. `cd temporal-py-grant-review` and `cp .env.example .env`; put your `OPENAI_API_KEY` in it (the repo-root `.env`
   also works).
2. `uv run python -m grantreview` (about 30 s; the first run also downloads the Temporal dev server, no Docker).
   It uses ports 4240 (gRPC) and 4241 (UI); override with `TEMPORAL_PORT` / `TEMPORAL_UI_PORT`.
3. `uv run python -m grantreview.verify` to check what landed in Opik.
4. Open the project in Opik. For Opik Cloud set `OPIK_API_KEY`, `OPIK_WORKSPACE` and `OPIK_OTLP_ENDPOINT`.
5. Tests: `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.

## Poke around

- Make the flakiness worse: in `activities.py` change `attempt == 1` to `attempt <= 3` and watch four
  `RunActivity:check_eligibility` spans appear (three red, one green; `RETRY` allows four attempts).
- Set `maximum_attempts=1` in `workflows.py`: the activity error fails the workflow and you can see where the
  trace stops.
- Edit `SCORE_SYSTEM` in `llm.py` to be generous and compare the `score-application` output of GR-2042.
- Start the worker by hand with `uv run python -m grantreview.worker` against your own dev server
  (`TEMPORAL_ADDRESS`) to see two separately started services share a trace.

## Gotchas we hit

**Every span shows up twice.** The first run had 22 spans in GR-2041 instead of 13: two `StartActivity`, four
`RunActivity:check_eligibility`, two `CompleteWorkflow`. Cause: the interceptor was passed to both
`Client.connect(..., interceptors=[i])` and `Worker(..., interceptors=[i])`, but a `Worker` adopts its client's
interceptors, so the tracing ran twice. Fix: pass it to the client only, as in `worker.py`.

**The trace Input/Output and the llm span output are empty.** Spans arrived with the model and tokens but no
messages. Cause: Opik's OTel mapper matches `gen_ai.prompt` and `gen_ai.completion` as exact keys, so indexed
keys such as `gen_ai.prompt.0.content` become loose attributes. Fix: set `gen_ai.prompt` and `gen_ai.completion`
to JSON strings, and set `input` / `output` on the client's root span so the trace columns fill.

## How it's put together

- `grantreview/models.py`, `data.py` - dataclasses and the fictional applications, register and rules.
- `grantreview/workflows.py` - the durable `GrantReviewWorkflow` and the retry policy.
- `grantreview/activities.py` - eligibility (with the flaky register lookup), scoring, letter.
- `grantreview/llm.py` - the two OpenAI calls, each wrapped in an llm span.
- `grantreview/tracing.py` - OTLP exporter to Opik, Temporal interceptor, root and llm span helpers.
- `grantreview/worker.py`, `demo.py` - the worker process and the client that spawns it.
- `grantreview/verify.py` - reads the project back from Opik and checks the trace shape.
- `tests/test_app.py` - rules, retry, score parsing, and an instrumented call with tracing off.

*built with Opik · inspired by Opik's examples and documentation*
