import { defineConfig } from "vitest/config";

export default defineConfig({
  // OPIK_TRACK_DISABLE=true is the Opik SDK's switch for turning tracing off. Setting it here means
  // `npm test` never logs to whatever Opik server the developer's shell points at.
  test: { env: { OPIK_TRACK_DISABLE: "true" } },
});
