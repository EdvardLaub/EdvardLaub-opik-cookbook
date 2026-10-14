# langchainjs-ollama-garden-rag

![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
![LangChain.js](https://img.shields.io/badge/LangChain.js-1.x-1C3C3C?style=flat)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2%3A1b-grey?style=flat)
![Opik](https://img.shields.io/badge/Opik-2.2.100-2f54eb?style=flat)

*A rulebook assistant for a community garden that runs entirely on your laptop, with a trace you can actually read.*

Nobody at Marrow Lane Community Garden wants to read the rulebook, so everybody asks the committee instead:
"can I use a hose?", "is it too early for tomatoes?", "what goes in the bins?". This example is an assistant
that answers from the garden's own notes. Embeddings and answers both come from models served by Ollama on your
machine, so there is **no cloud LLM call anywhere** and no provider key to set up.

Tracing a pipeline like that raises two small questions. What does an Opik trace look like when there is no
hosted model, no token bill, nothing to price? And what happens to the retrieval step when your vector store is
ordinary TypeScript rather than a LangChain retriever? The answer to the second one is: it silently vanishes from
the trace, and you have to put it back deliberately.

## What you'll build

A TypeScript RAG app, split into four small modules instead of one script:

- a loader and chunker that turns four markdown files in `docs/` (plot rules, watering rota, composting, planting
  calendar) into one chunk per `##` section;
- a tiny in-memory vector store that embeds chunks with `nomic-embed-text` and ranks them by cosine similarity;
- a chain (`GardenAssistant`) that retrieves two chunks, fills a prompt, and asks `llama3.2:1b` through
  `ChatOllama`;
- a CLI that answers three demo questions, or one question you pass on the command line.

Tracing is `OpikCallbackHandler` from `opik-langchain`, passed as a LangChain callback. Retrieval is wrapped as a
named LangChain tool, `search_garden_docs`, so that it is recorded as its own step.

## See it in Opik

Open the **langchainjs-ollama-garden-rag** project and look at the Traces tab. Each question is one trace called
`ask_the_garden`. Expand it and you will find a `search_garden_docs` span of type tool (the retrieval step),
followed by a `ChatPromptTemplate` span, an llm span called `ChatOllama` with model `llama3.2:1b` and the full
prompt and answer, and an output-parser span.

The llm span has no token counts and no cost. That is expected: the Ollama integration does not report usage to
the callback, so with a local model the trace is about *what happened*, not what it cost.

## Run it yourself

You need Node 22+, a running Ollama, and an Opik to send traces to.

1. Run Ollama yourself, either the native install or the `ollama/ollama` Docker image, and pull the two models:
   `ollama pull llama3.2:1b` and `ollama pull nomic-embed-text`. The app expects it at `http://localhost:11434`
   (override with `OLLAMA_URL`).
2. `npm install`
3. `cp .env.example .env` (the defaults point at a local Opik at `http://localhost:5173/api/`; set `OPIK_API_KEY`
   and drop `OPIK_URL_OVERRIDE` to use Opik Cloud). The repo-root `.env` is read too.
4. `npm run demo` answers three questions. `npm run ask -- "Can dogs come to the garden?"` answers your own.
5. Open the project in Opik.

Inference is CPU-bound with a 1B model, so expect a few minutes for the three questions, mostly model loading.

## Poke around

- Ask something the notes do not cover ("Can I keep chickens?") and open the `search_garden_docs` span: the top two
  chunks are the closest in meaning, not relevant. See whether the 1B model admits it does not know.
- Change `TOP_K` in `src/chain.ts` to 1 and re-ask the compost question. Watch the answer lose items.
- Edit `docs/watering-rota.md` (say, allow hoses in April) and re-run: the answer follows your edit.
- Swap `CHAT_MODEL` for `llama3.2:3b` and compare two traces of the same question side by side.

## Gotchas we hit

**`npm install` fails with `ERESOLVE ... peer opik@"^1.8.75" from opik-langchain@2.2.100`.** `opik-langchain` still
declares an old peer range for `opik`. Add an override so it uses the `opik` you installed:

```json
"overrides": { "opik-langchain": { "opik": "$opik" } }
```

**The retrieval step is missing from the trace.** `OpikCallbackHandler` only sees LangChain runs. A vector store you
wrote yourself is not one, so its search never reaches the callback and the retrieved text only shows up buried in
the prompt. Run the search through a named LangChain tool (`tool(...)` in `src/chain.ts`) and invoke it with the
chain's `config`, so it appears as a tool span nested in the trace.

## How it's put together

- `src/loader.ts`: reads `docs/*.md` and splits each file into one chunk per `##` section.
- `src/store.ts`: `VectorStore`, an in-memory cosine-similarity index over an `Embedder`.
- `src/chain.ts`: `GardenAssistant`, the prompt, the `search_garden_docs` tool and the Ollama models.
- `src/tracing.ts`: creates the `OpikCallbackHandler` bound to this example's project.
- `src/cli.ts`: loads `.env`, checks Ollama is up, runs the questions, flushes traces.
- `docs/`: the fictional garden rulebook and planting calendar.
- `tests/`: vitest, offline: chunking, similarity ranking, retrieval, prompt, and `ask` with a fake chat model and
  the Opik handler attached. `npm test` sets `OPIK_TRACK_DISABLE=true` (in `vitest.config.ts`) so nothing is sent.

---

*built with Opik · inspired by Opik's examples and documentation*
