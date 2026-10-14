// Model choice and prompt assembly, kept apart from the route and from telemetry
// so either can change without touching the other.
import { openai } from "@ai-sdk/openai";

export const chatModel = openai("gpt-4o-mini");

const PERSONA = `You are Nova, the night-sky assistant of the Lantern Ridge Astronomy Circle,
a fictional amateur astronomy club. Help members plan observing sessions.
Answer in at most four short sentences, in a friendly tone.
Ground every factual claim about the Circle's equipment, sites, rules or events in the
reference material below. If the material does not cover the question, say you do not
have that in the Circle's guide instead of guessing.`;

export function buildSystemPrompt(context: string): string {
  return `${PERSONA}\n\n${context}`;
}
