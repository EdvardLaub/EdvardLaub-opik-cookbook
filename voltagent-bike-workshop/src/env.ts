// Loads the example's .env, then the repo-root .env, before anything else
// reads process.env.
import { config } from "dotenv";
import { fileURLToPath } from "node:url";

config({
  path: [
    fileURLToPath(new URL("../.env", import.meta.url)),
    fileURLToPath(new URL("../../.env", import.meta.url)),
  ],
  quiet: true,
});

// Talk to the public OpenAI API even if a local proxy is configured.
delete process.env.OPENAI_BASE_URL;
