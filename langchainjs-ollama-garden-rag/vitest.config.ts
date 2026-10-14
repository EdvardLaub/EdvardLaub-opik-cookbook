import { defineConfig } from "vitest/config";

export default defineConfig({
  // OPIK_TRACK_DISABLE=true is the Opik SDK's switch for turning tracing off. Setting it here keeps
  // `npm test` from logging anything to whichever Opik your shell points at.
  test: { env: { OPIK_TRACK_DISABLE: "true" } },
});
