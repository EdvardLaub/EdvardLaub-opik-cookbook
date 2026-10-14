# otel-py-homebrew-rag

*A home-brewing FAQ service traced into Opik with nothing but OpenTelemetry, and the one switch that decides whether the traces contain any text.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-OTLP-009688?style=flat&logo=fastapi&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-SDK-425CC7?style=flat&logo=opentelemetry&logoColor=white)

## The problem

You point an OpenTelemetry exporter at Opik, the spans arrive, tokens and cost are filled in, and then you open a trace and the Input and Output columns are blank. Nothing is broken. The OpenAI instrumentation deliberately leaves prompts and completions off spans unless you opt in, and Opik fills a trace's Input/Output from the *root* span's attributes, which your instrumentation never writes. This example builds a small service, shows the empty version, then fixes it, and nothing in it uses the Opik SDK: it is OTLP all the way.

## What you'll build

A FastAPI service (`POST /ask`) that answers questions from the fictional *Hollowbrook Brewing Guide*, five short chapters in `docs/` on mashing, fermentation temperatures, sanitising, bottling and off-flavours. At startup it embeds each section with `text-embedding-3-small` into an in-memory index; each question retrieves the 3 closest sections and `gpt-4o-mini` answers from them only ("I don't know" otherwise).

Tracing is the OpenTelemetry SDK, an OTLP/HTTP exporter aimed at Opik's OTel endpoint, and `opentelemetry-instrumentation-openai-v2` for the OpenAI calls (`brewfaq/telemetry.py`). FastAPI emits its own server span, and the app adds one manual `retrieve` span. A demo script boots the server twice (content capture off, then on), asks scripted questions over HTTP, and shuts it down cleanly so the exporter flushes.

## See it in Opik

Open the project **otel-py-homebrew-rag** in a local Opik. One demo run leaves 7 traces: 5 `POST /ask` traces and 2 `embeddings` traces (one per server boot, the startup indexing, 1,242 tokens each).

- **The empty one.** The oldest `POST /ask` trace is the capture-off pass. Its Output column is empty, and its Input shows only the HTTP server attributes (method, route, port, status code), with no trace of the question. Open it: the `chat gpt-4o-mini` span is there, typed `llm`, with 335 prompt + 15 completion tokens and an estimated cost of about $0.00006, but its input holds only response metadata (service tier, system fingerprint) and its output is empty. The `retrieve` span has no input or output either. The only hint is a `brewfaq.content_capture: off` attribute on the root.
- **The full ones.** The four newer `POST /ask` traces (capture on) show the question as the trace Input and the answer as the Output. Expand one: `retrieve` outputs the chunks it picked with their scores (for the butterscotch question, `05-off-flavours.md: Buttery or butterscotch (diacetyl) (0.71)` first), and `chat gpt-4o-mini` shows the full system prompt, the excerpts and the question as input and the completion as output. The out-of-guide question about hazy IPA hops retrieves weak matches (best score 0.40) and the model answers "I don't know."
- **Cost.** All llm spans, including embeddings, carry usage and a computed cost (about $0.00036 for the whole run), because the instrumentation sets the `openai` provider attribute that Opik uses for pricing.

## Run it yourself

1. Install [uv](https://docs.astral.sh/uv/) and have a local Opik running at `http://localhost:5173` (workspace `default`, no key).
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a repo-root `.env` also works).
3. `uv sync`
4. `uv run python -m brewfaq.demo`. It takes about 10 seconds and costs a fraction of a cent.
5. To run the server yourself: `uv run python -m brewfaq.server`, then
   `curl -s localhost:4430/ask -H 'content-type: application/json' -d '{"question":"How hot should I sparge?"}'`.
   Add the two `OTEL_*` variables from `.env.example` to see content on the spans.
6. Tests (offline, no keys): `env -u OPENAI_API_KEY OTEL_SDK_DISABLED=true uv run pytest`

## Poke around

- Set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only` but drop `OTEL_SEMCONV_STABILITY_OPT_IN` and compare what the chat span holds.
- Comment out `set_trace_io(...)` in `server.py` and see the trace columns fall back to the HTTP attributes of the server span.
- Ask something a brewer would phrase badly ("why does my beer taste like nail polish remover?") and read the `retrieve` scores.
- Change `OPIK_PROJECT_NAME` and watch a second project appear.

## Gotchas we hit

**`ModuleNotFoundError: No module named 'opentelemetry.util.genai.instruments'`** on importing the instrumentation. `opentelemetry-instrumentation-openai-v2` 2.4b0 imports a module that the newest `opentelemetry-util-genai` 1.2b0 made private. Pin the older one: `"opentelemetry-util-genai==1.1b0"` (see `pyproject.toml`).

**Spans arrive but every Input and Output is empty.** Prompt and completion content is off by default. Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only` before the process starts. With those, the chat span's input/output land in Opik as `messages` with `parts`.

**The llm spans are full but the trace Input/Output columns are still empty.** Opik reads them from the root span's `input` / `output` attributes. Here the root is FastAPI's own `POST /ask` span, which you do not create, so `telemetry.py` keeps a tiny `SpanProcessor` that remembers each open root span and `set_trace_io()` writes the attributes onto it. Those attributes follow the same capture switch as the instrumentation.

**Embedding spans show only `gen_ai.embeddings.dimension.count`.** With these versions the instrumentation does not record the embedded text, even with capture on, so only token usage and cost appear for them. The retrieval text is visible on the manual `retrieve` span instead.

**Extra spans.** FastAPI's own `fastapi.endpoint`, `fastapi.dependencies` and `fastapi.serialization` spans also arrive as empty `general` spans, and any HTTP request (a health check, say) becomes its own trace. The demo waits for the port instead of polling `/health` for this reason.

## How it's put together

- `docs/` the fictional brewing guide, five chapters.
- `brewfaq/corpus.py` loads the guide and splits it into sections.
- `brewfaq/rag.py` embeddings, cosine retrieval and the chat call.
- `brewfaq/server.py` the FastAPI app and the `retrieve` span.
- `brewfaq/telemetry.py` OTel SDK, OTLP exporter to Opik, OpenAI instrumentation, root-span input/output.
- `brewfaq/demo.py` boots the server, asks scripted questions with capture off then on, shuts it down.
- `tests/test_logic.py` offline tests: chunking, ranking, prompt formatting, the capture switch, and the traced `/ask` endpoint with the SDK disabled.

*built with Opik · inspired by Opik's examples and documentation*
