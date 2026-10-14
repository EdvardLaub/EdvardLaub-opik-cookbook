import { config } from "dotenv";
import { fileURLToPath } from "node:url";

/** Load this folder's .env, then the parent's. dotenv never overrides variables already set. */
export function loadEnv(): void {
  const here = fileURLToPath(new URL(".", import.meta.url));
  config({ path: [`${here}../.env`, `${here}../../.env`], quiet: true });
}
