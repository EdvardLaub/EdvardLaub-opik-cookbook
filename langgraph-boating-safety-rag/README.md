# langgraph-boating-safety-rag

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/langgraph-1.2-1C3C3C?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2-2f54eb?style=flat)](https://github.com/comet-ml/opik)

**A harbor-safety Q&A bot whose every answer you can audit: what it fetched, what it said, and how a judge scored it.**

A skipper asking "do kids need a life jacket in the cabin?" deserves an answer
that comes from the handbook, not from the model's imagination. This example
puts a small retrieval-augmented assistant in front of a fictional handbook
(*Marrowbay Waterways*: life jackets, right of way, weather, VHF radio,
fueling) and uses Opik to show both halves of RAG quality: did retrieval
fetch the right passages, and did the answer stay inside them?

## What you'll build

The app is split into small modules:

- a **corpus loader** that cuts five markdown chapters into one chunk per section,
- a **retriever** (in-memory vector store, OpenAI embeddings, top-3),
- a two-node **LangGraph** graph, `retrieve` then `generate` (`gpt-4o-mini`),
- an **eval** module with an 8-question Opik dataset and an experiment scored by
  the `Hallucination` and `ContextPrecision` judges.

## See it in Opik

Open the `langgraph-boating-safety-rag` project. The **Traces** tab holds 12
traces after one run: 4 named `LangGraph` (the demo questions) and 8 named
`evaluation_task` (one per dataset item). Click a `LangGraph` trace: the tree
has `retrieve` and `generate` node spans, and under `generate` a `ChatOpenAI`
span of type `llm` with the exact prompt, the handbook excerpts, token usage
and cost (about $0.00006 to $0.0002 per call). The `retrieve` span's output is
the three chunks fetched.

Under **Experiments**, `rag-top3` links to the `boating-safety-questions`
dataset (8 items). Its averages: `hallucination_metric` 0.00 (nothing
unsupported by the retrieved text) and `context_precision_metric` 0.70.
The waterfowl-licence question is the odd one out: the handbook is silent, and
the assistant answers "I don't know".

## Run it yourself

1. Start a local Opik (or set `OPIK_API_KEY` / `OPIK_WORKSPACE` for Opik Cloud).
2. `cp .env.example .env` and set `OPENAI_API_KEY` (a `.env` in a parent folder also works).
3. `uv sync`
4. `uv run main.py`
5. Open the project in Opik and look at Traces, then Experiments.

A full run takes about 30 seconds and costs well under a cent.

## Poke around

- Run `RAG_TOP_K=1 uv run main.py`: the new `rag-top1` experiment can be compared with `rag-top3`.
- Edit a number in `data/vhf-radio.md` and watch the answer repeat it with a clean hallucination score: the judge checks the answer against the retrieved text, not against the truth.
- Add a question to `DATASET_ITEMS` in `boating_rag/evaluation.py` for something the handbook does not cover.

## Gotchas we hit

**`ImportError: cosine_similarity requires numpy to be installed`** raised
inside the `retrieve` node. `InMemoryVectorStore` imports numpy lazily and
`langchain-core` does not depend on it. Add `numpy` to your dependencies.

## How it's put together

- `main.py`: demo questions, then the experiment; sets the Opik project and flushes.
- `boating_rag/corpus.py`: splits the handbook into section chunks.
- `boating_rag/retriever.py`: embeds chunks, returns the top-k.
- `boating_rag/graph.py`: the retrieve/generate graph, wrapped with `track_langgraph`.
- `boating_rag/evaluation.py`: dataset items, task wrapper, `evaluate()` call.
- `data/`: five fictional handbook chapters.
- `tests/test_rag.py`: offline tests with fake embeddings and a stub model. Run `env -u OPENAI_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`.

*built with Opik · inspired by Opik's examples and documentation*
