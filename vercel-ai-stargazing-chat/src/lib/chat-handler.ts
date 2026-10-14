// The chat route handler: parse the useChat payload, ground the prompt, stream.
import { streamText, convertToModelMessages, type LanguageModel, type UIMessage } from "ai";
import { chatModel, buildSystemPrompt } from "./model";
import { buildContext } from "./knowledge";
import { telemetrySettings } from "./telemetry";
import { TRACE_NAME } from "./config";

export function lastUserText(messages: UIMessage[]): string {
  const last = [...messages].reverse().find((m) => m.role === "user");
  return (last?.parts ?? []).map((p) => (p.type === "text" ? p.text : "")).join(" ").trim();
}

export async function handleChat(req: Request, model: LanguageModel = chatModel): Promise<Response> {
  // useChat (and the demo script) sends the chat id plus the full history each turn.
  const { id, messages } = (await req.json()) as { id: string; messages: UIMessage[] };

  const result = streamText({
    model,
    system: buildSystemPrompt(buildContext(lastUserText(messages))),
    messages: await convertToModelMessages(messages),
    // The chat id rides in runtimeContext and becomes the Opik thread id, so all
    // turns of one conversation show up under Threads instead of as loose traces.
    runtimeContext: { threadId: id, traceName: TRACE_NAME },
    experimental_telemetry: telemetrySettings(),
  });

  return result.toUIMessageStreamResponse();
}
