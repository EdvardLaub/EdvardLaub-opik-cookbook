# EdvardLaub-opik-cookbook

**Twenty small LLM apps, each one cooked until its traces, scores and costs show up in [Opik](https://github.com/comet-ml/opik).**

[![Opik](https://img.shields.io/badge/observability-Opik-2f54eb?style=flat)](https://www.comet.com/docs/opik/)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-strict-3178C6?style=flat&logo=typescript&logoColor=white)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat)](LICENSE)

Most "add observability to your LLM app" snippets stop at `pip install`. The interesting part comes later:
the trace whose Output column is empty, the cost that reads `null`, the test suite that passes on Tuesday and
fails on Wednesday, or the retriever span that never shows up. Every recipe here is a complete, runnable app
with a made-up domain and its own data. Each one was run against a real Opik and then written up with what
actually appeared, including the parts that went wrong.

Pick a recipe by what you want to learn, not by framework.

## The menu

### Seeing what the app did (tracing)

| Recipe | Stack | What it shows |
|---|---|---|
| [`openai-ts-museum-guide-chat`](openai-ts-museum-guide-chat) | TypeScript · OpenAI + `opik-openai` | Conversations as Opik threads, cost per turn, a feedback score logged after the chat |
| [`openai-agents-campus-services`](openai-agents-campus-services) | Python · OpenAI Agents SDK | Triage → specialist handoffs and tool calls, grouped into threads |
| [`mastra-banking-agent`](mastra-banking-agent) | TypeScript · Mastra (OTel) | Agent-loop trees with real `execute_tool` spans, plus the provider mapping that makes cost appear |
| [`langgraph-postmortem-team`](langgraph-postmortem-team) | Python · LangGraph | One deep trace with a visible investigation loop and cost per agent |
| [`temporal-py-grant-review`](temporal-py-grant-review) | Python · Temporal | One trace across a client and a worker process, with the failed attempt and its retry |
| [`smolagents-solar-output-analyst`](smolagents-solar-output-analyst) | Python · smolagents (OpenInference) | The pandas code a CodeAgent wrote, and why it got one answer wrong |
| [`beeai-py-expense-triage`](beeai-py-expense-triage) | Python · BeeAI | ReAct iterations, LLM and tool spans, with per-trace correctness scores |
| [`whisper-vet-voicemail-triage`](whisper-vet-voicemail-triage) | Python · OpenAI TTS + Whisper | A playable MP3 attached to every trace |
| [`langchainjs-ollama-garden-rag`](langchainjs-ollama-garden-rag) | TypeScript · LangChain.js + Ollama | Fully local RAG with zero cloud calls, and the retrieval span the callback misses |

### Knowing whether it's good (evaluation)

| Recipe | Stack | What it shows |
|---|---|---|
| [`anthropic-ts-espresso-manual-qa`](anthropic-ts-espresso-manual-qa) | TypeScript · Anthropic SDK (manual tracing) | A test suite of plain-English citation assertions, three runs per question |
| [`pydantic-ai-lost-and-found-intake`](pydantic-ai-lost-and-found-intake) | Python · Pydantic AI (OTel) | A suite that catches invented field values, with one honest failure left in |
| [`langgraph-boating-safety-rag`](langgraph-boating-safety-rag) | Python · LangChain + LangGraph | Dataset + experiment scored for hallucination and context precision |
| [`openai-vision-shipping-labels`](openai-vision-shipping-labels) | Python · OpenAI vision | Label images as attachments, and a suite that keeps its failures (6/8) |
| [`vercel-ai-stargazing-chat`](vercel-ai-stargazing-chat) | TypeScript · Vercel AI SDK + Next.js | Streaming chat with a live online-evaluation rule scoring each turn |

### Making it better (prompts and optimization)

| Recipe | Stack | What it shows |
|---|---|---|
| [`opik-ts-changelog-prompts`](opik-ts-changelog-prompts) | TypeScript · Opik SDK | Prompt-library versions with a diff, and a suite going from 0% to 100% across them |
| [`dspy-claim-verifier`](dspy-claim-verifier) | Python · DSPy | The same suite before and after compiling: 0/8 → 7/8 |
| [`optimizer-wildlife-report-classifier`](optimizer-wildlife-report-classifier) | Python · Opik Agent Optimizer | A score curve across trials, with the winning prompt saved to the library |

### Without the Opik SDK (OpenTelemetry and low-code)

| Recipe | Stack | What it shows |
|---|---|---|
| [`otel-py-homebrew-rag`](otel-py-homebrew-rag) | Python · FastAPI + OpenTelemetry only | The one switch that decides whether your traces contain any content |
| [`voltagent-bike-workshop`](voltagent-bike-workshop) | TypeScript · VoltAgent (OTel) | The `gen_ai.*` attribute mapping that makes usage and cost land |
| [`dify-theater-box-office`](dify-theater-box-office) | Low-code · Dify in Docker | Platform-level tracing switched on through Dify's API: no app code, one Opik thread per conversation |

## Running a recipe

Every recipe expects a running Opik. The quickest way to get one is to run Opik locally
([self-hosting guide](https://www.comet.com/docs/opik/self-host/local_deployment)), which is what these were built
against. Opik Cloud works too: set `OPIK_URL_OVERRIDE` and `OPIK_API_KEY`.

```bash
cp .env.example .env        # add OPENAI_API_KEY (and ANTHROPIC_API_KEY for the Anthropic recipe)
cd <recipe>
uv run main.py              # Python recipes (some use a CLI; each README has the exact command)
npm install && npm run demo # TypeScript recipes
```

Each recipe reads the single `.env` at the repo root, so you set your keys once.

## What's in each recipe

- **A short commit history.** Most recipes land as a few commits: the plain app first, then Opik tracing, then
  the evaluation layer. Run `git log -- <recipe>` to see exactly what "adding Opik" changed.
- **Comments at every Opik call** saying what it produces in the UI and what breaks without it.
- **A "Gotchas" section** with real symptom → cause → fix entries, hit while building against the pinned versions.
- **Offline tests** (`uv run pytest` / `npm test`) that pass with no API keys and Opik tracking disabled.
- **Fictional data only.** Every museum, bank, garden and theater here is made up.

---

<sub>Built with Opik · inspired by Opik's examples and documentation · [github.com/comet-ml/opik](https://github.com/comet-ml/opik) · [docs](https://www.comet.com/docs/opik/)</sub>
