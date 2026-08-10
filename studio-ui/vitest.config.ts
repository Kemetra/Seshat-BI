import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Test configuration, separate from `vite.config.ts` on purpose.
 *
 * Vitest 2 bundles its own nested Vite, so a single config that imports
 * `defineConfig` from one and is consumed by the other fails typechecking: the two
 * `UserConfig` types are structurally incompatible under
 * `exactOptionalPropertyTypes`. Two files, each typed by its own tool, is the fix that
 * keeps strict mode on rather than loosening it.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    css: false,
  },
});
