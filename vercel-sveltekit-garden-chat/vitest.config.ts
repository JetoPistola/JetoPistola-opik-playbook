import { defineConfig } from "vitest/config";
import path from "node:path";

// Plain vitest (no SvelteKit plugin): only the $lib alias is needed for the server code.
export default defineConfig({
  resolve: { alias: { $lib: path.resolve("src/lib") } },
  test: { include: ["tests/**/*.test.ts"] },
});
