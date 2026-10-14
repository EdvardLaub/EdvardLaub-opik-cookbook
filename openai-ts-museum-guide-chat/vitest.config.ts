import { defineConfig } from "vitest/config";

export default defineConfig({
  // OPIK_TRACK_DISABLE=true is the Opik SDK's switch to turn tracing off. Setting it here means
  // `npm test` does not log test runs to whatever Opik the developer's shell points at.
  test: { env: { OPIK_TRACK_DISABLE: "true" } },
});
