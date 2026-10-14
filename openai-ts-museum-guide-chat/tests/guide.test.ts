import { describe, expect, it } from "vitest";
import type OpenAI from "openai";
import { Opik } from "opik";
import { MuseumGuide } from "../src/guide.js";

// A stand-in for the OpenAI client: records what it was sent and replies with canned text.
function fakeOpenAI(replies: string[]) {
  const calls: { role: string; content: string }[][] = [];
  const client = {
    chat: {
      completions: {
        create: async (args: { messages: { role: string; content: string }[] }) => {
          calls.push(args.messages.map((m) => ({ ...m })));
          return { id: "x", choices: [{ index: 0, message: { role: "assistant", content: replies[calls.length - 1] } }] };
        },
      },
    },
  };
  return { client: client as unknown as OpenAI, calls };
}

describe("MuseumGuide.ask (Opik tracking disabled)", () => {
  // vitest.config.ts sets OPIK_TRACK_DISABLE=true, so these runs are not logged to Opik. The
  // traced code path (trace() + the trackOpenAI wrapper) still executes and must not break the app.

  it("returns the reply and keeps the whole conversation as memory", async () => {
    const { client, calls } = fakeOpenAI(["We open at 09:00.", "Yes, step-free."]);
    const guide = new MuseumGuide(client, new Opik({ projectName: "offline-test" }), "thread-1");

    const first = await guide.ask("When do you open on Saturday?");
    await guide.ask("Is it step-free?");

    expect(first.reply).toBe("We open at 09:00.");
    expect(first.traceId).toBeTruthy();
    expect(calls[0]!.map((m) => m.role)).toEqual(["system", "user"]);
    // second call re-sends system + user + assistant + user
    expect(calls[1]!.map((m) => m.role)).toEqual(["system", "user", "assistant", "user"]);
    expect(calls[1]![2]!.content).toBe("We open at 09:00.");
  });
});
