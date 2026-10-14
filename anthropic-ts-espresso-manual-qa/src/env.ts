import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/** Load the nearest .env found walking up from this folder (never overrides the shell). */
export function loadEnv(): void {
  let dir = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 4; i++) {
    const candidate = path.join(dir, ".env");
    if (fs.existsSync(candidate)) {
      process.loadEnvFile(candidate);
      break;
    }
    dir = path.dirname(dir);
  }
  // Some dev setups point ANTHROPIC_BASE_URL at a proxy; this example talks to the real API.
  delete process.env.ANTHROPIC_BASE_URL;
}
