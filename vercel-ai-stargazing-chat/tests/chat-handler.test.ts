import { describe, expect, it } from "vitest";
import { MockLanguageModelV4, simulateReadableStream } from "ai/test";
import type { UIMessage } from "ai";
import { handleChat, lastUserText } from "../src/lib/chat-handler";

const messages: UIMessage[] = [
  { id: "1", role: "user", parts: [{ type: "text", text: "Which loaner is better for the Orion Nebula?" }] },
];

describe("chat handler", () => {
  it("extracts the latest user text", () => {
    expect(lastUserText(messages)).toMatch(/Orion/);
  });

  it("streams a reply and grounds the prompt, with a stubbed model and no tracing registered", async () => {
    const model = new MockLanguageModelV4({
      doStream: async () => ({
        stream: simulateReadableStream({
          chunks: [
            { type: "text-start", id: "a" },
            { type: "text-delta", id: "a", delta: "Pip works nicely." },
            { type: "text-end", id: "a" },
            {
              type: "finish",
              finishReason: { unified: "stop", raw: "stop" },
              usage: {
                inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
                outputTokens: { total: 4, text: 4, reasoning: 0 },
              },
            },
          ],
        }),
      }),
    } as never);
    const res = await handleChat(
      new Request("http://test/api/chat", { method: "POST", body: JSON.stringify({ id: "chat-1", messages }) }),
      model as never,
    );
    expect(await res.text()).toContain("Pip works nicely.");
    expect(JSON.stringify(model.doStreamCalls[0]?.prompt)).toContain("Loaner telescopes");
  });
});
