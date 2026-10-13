import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Opik's documented switch: with this set the SDK records and sends nothing.
    env: { OPIK_TRACK_DISABLE: "true" },
    // main.ts reads data/ relative to the cwd, so the run test chdir()s;
    // that needs real processes, not worker threads.
    pool: "forks",
  },
});
