import { config } from "dotenv";
import { fileURLToPath } from "node:url";

export const PROJECT_NAME = "opik-ts-changelog-prompts";

/** Load this folder's .env, then the parent's. dotenv never overrides variables already set. */
export function loadEnv(): void {
  const here = fileURLToPath(new URL(".", import.meta.url));
  config({ path: [`${here}../.env`, `${here}../../.env`], quiet: true });
  // Default Opik project for every trace and prompt this app creates. The Opik SDK reads it when a
  // client is created; without it, traces would land in the "Default Project".
  process.env.OPIK_PROJECT_NAME ??= PROJECT_NAME;
}
