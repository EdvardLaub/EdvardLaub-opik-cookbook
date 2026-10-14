import { describe, expect, it } from "vitest";
import { formatContext, prompt } from "../src/chain.js";
import { createHandler } from "../src/tracing.js";
import { offlineAssistant } from "./helpers.js";

describe("retrieval step", () => {
  it("returns chunk ids and scores through the tool's artifact", async () => {
    const assistant = await offlineAssistant();
    const hits = await assistant.retrieve("When can I plant out tomatoes after the frost?");
    expect(hits[0]?.chunk.source).toBe("planting-calendar");
    expect(hits.length).toBe(2);
  });
});

describe("prompt", () => {
  it("puts the retrieved notes and the question into the messages", async () => {
    const assistant = await offlineAssistant();
    const hits = await assistant.retrieve("What can't go in the compost?");
    const messages = await prompt.formatMessages({ context: formatContext(hits), question: "What can't go in the compost?" });
    expect(String(messages[0]?.content)).toContain("Composting");
    expect(String(messages[1]?.content)).toBe("What can't go in the compost?");
  });
});

describe("ask", () => {
  it("answers without any callbacks", async () => {
    expect(await (await offlineAssistant("no tracing")).ask("hose?")).toBe("no tracing");
  });

  it("still answers when the Opik handler is attached and tracking is disabled", async () => {
    // OPIK_TRACK_DISABLE=true (set in vitest.config.ts) makes the SDK drop everything the handler records.
    const answer = await (await offlineAssistant("traced answer")).ask("hose?", [createHandler()]);
    expect(answer).toBe("traced answer");
  });
});
