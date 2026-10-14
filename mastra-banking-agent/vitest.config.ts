import { defineConfig } from "vitest/config";

export default defineConfig({
  // Tests must run with no keys and no Opik: tracking is switched off for the whole suite.
  test: { env: { OPIK_TRACK_DISABLE: "true" }, testTimeout: 20000 },
});
