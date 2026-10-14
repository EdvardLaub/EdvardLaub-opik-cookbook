import type OpenAI from "openai";
import type { Opik } from "opik";
import { trackOpenAI } from "opik-openai";
import { buildSystemPrompt } from "./museum.js";

export const MODEL = "gpt-4o-mini";

export interface Turn {
  reply: string;
  traceId: string;
}

type Message = { role: "system" | "user" | "assistant"; content: string };

/**
 * One instance per visitor conversation. It keeps the message history as memory, and
 * every call to ask() becomes one Opik trace carrying this conversation's thread id.
 */
export class MuseumGuide {
  private readonly messages: Message[] = [{ role: "system", content: buildSystemPrompt() }];

  constructor(
    private readonly openai: OpenAI,
    private readonly opik: Opik,
    readonly threadId: string,
  ) {}

  async ask(userMessage: string): Promise<Turn> {
    this.messages.push({ role: "user", content: userMessage });

    // One trace per turn. threadId is what the Threads tab groups by: traces that share it
    // are shown as one conversation. Without it each turn is an unrelated row.
    const trace = this.opik.trace({
      name: "answer-visitor-question",
      threadId: this.threadId,
      input: { message: userMessage },
    });

    // trackOpenAI(parent: trace) nests the completion under this trace as a span named
    // "guide-reply" (type general in this SDK version) with model, token usage and estimated
    // cost. Without parent it would not attach to our per-turn trace. The wrapper is per turn because the
    // parent is fixed when the client is wrapped.
    const tracked = trackOpenAI(this.openai, {
      client: this.opik,
      parent: trace,
      generationName: "guide-reply",
    });
    const response = await tracked.chat.completions.create({
      model: MODEL,
      messages: this.messages,
    });
    await tracked.flush(); // ship the llm span before we close the trace

    const reply = response.choices[0]?.message?.content ?? "";
    this.messages.push({ role: "assistant", content: reply });

    // Fill in the output column, then close the trace so it has an end time and duration.
    trace.update({ output: { reply } });
    trace.end();

    // Trace has .data.id (not .id); keep it so a feedback score can target this turn later.
    return { reply, traceId: trace.data.id };
  }
}
