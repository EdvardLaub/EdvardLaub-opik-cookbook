import { OpikCallbackHandler } from "opik-langchain";

export const PROJECT = "langchainjs-ollama-garden-rag";

/**
 * One handler per run. Passed as a LangChain callback, it turns each chain invocation into an Opik
 * trace: a root span for the chain, nested llm spans for ChatOllama (prompt, answer, model name).
 * projectName makes every trace land in this project instead of "Default Project".
 */
export function createHandler(): OpikCallbackHandler {
  return new OpikCallbackHandler({ projectName: PROJECT });
}
