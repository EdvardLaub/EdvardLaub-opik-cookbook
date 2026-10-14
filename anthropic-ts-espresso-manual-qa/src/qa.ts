import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";
import { getTrackContext, track } from "opik";
import { checkQuotes } from "./quotes.js";

export const PROJECT_NAME = "anthropic-ts-espresso-manual-qa";
export const MODEL = "claude-haiku-4-5";

export const MANUAL = fs.readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "docs", "manual.md"),
  "utf8",
);

export const SYSTEM_PROMPT = `You answer questions about the Marlowe Barista M2 espresso machine, \
using its owner's manual reproduced in full below.

Rules:
- Answer only from the manual. If the manual does not cover the question, say so plainly \
and do not quote anything.
- Every factual claim must be backed by a verbatim excerpt from the manual wrapped in \
<quote>...</quote> tags, copied character-for-character.
- Keep answers short: the answer first, then the supporting quote(s).

<manual>
${MANUAL}
</manual>`;

/** Lazily built so unit tests can import this module without an API key. */
let anthropic: Anthropic | undefined;
const getClient = () => (anthropic ??= new Anthropic());
/** Test seam: swap in a stub client. */
export const setClient = (client: Anthropic) => {
  anthropic = client;
};

// The Opik TS SDK has no Anthropic integration (only Python does), so we trace by hand.
// track() with type "llm" makes this call an llm span; enrichSpan copies the model, provider
// and token usage from the response onto it. Without provider + usage, Opik shows no tokens
// and cannot estimate cost.
export const callClaude = track(
  {
    name: "anthropic_messages_create",
    type: "llm",
    enrichSpan: (message: Anthropic.Message) => ({
      model: message.model,
      provider: "anthropic",
      usage: {
        prompt_tokens: message.usage.input_tokens,
        completion_tokens: message.usage.output_tokens,
        total_tokens: message.usage.input_tokens + message.usage.output_tokens,
      },
    }),
  },
  async (question: string): Promise<Anthropic.Message> =>
    getClient().messages.create({
      model: MODEL,
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: question }],
    }),
);

// track() on the outer function opens the trace (a general span) that nests the llm span.
export const answerQuestion = track(
  { name: "answer_question", type: "general" },
  async (question: string): Promise<string> => {
    const message = (await callClaude(question)) as Anthropic.Message;
    const block = message.content[0];
    const answer = block && block.type === "text" ? block.text : "";

    // A cheap deterministic check next to the LLM judge, logged as a feedback score on the
    // trace (a "quotes_verbatim" column in the traces table). Answers with no quotes at all
    // (e.g. "the manual doesn't cover that") get no score: there is nothing to verify.
    const check = checkQuotes(answer, MANUAL);
    if (check.quotes.length > 0) {
      getTrackContext()?.trace.score({
        name: "quotes_verbatim",
        value: check.allVerbatim ? 1 : 0,
        reason: check.missing.length ? `Not in manual: ${check.missing.join(" | ")}` : undefined,
      });
    }
    return answer;
  },
) as (question: string) => Promise<string>;
