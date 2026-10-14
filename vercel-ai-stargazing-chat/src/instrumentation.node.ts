import { config } from "dotenv";
import path from "node:path";

// Walk up to the repo-root .env (shared keys); never overrides variables already set.
config({ path: path.resolve(process.cwd(), "../.env"), quiet: true });
process.env.OPIK_URL_OVERRIDE ??= "http://localhost:5173/api/";
process.env.OPIK_WORKSPACE ??= "default";

// Imported only after the env is set: opik-vercel builds a default Opik client
// at import time and reads OPIK_URL_OVERRIDE / OPIK_WORKSPACE then.
const { registerOpik } = await import("./lib/telemetry");
registerOpik();
