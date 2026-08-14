import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

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
/**
 * `tokens.css` inlined as a string for `contrast.test.ts` (T032, FR-031).
 *
 * The audit needs the token TEXT, and the two in-test routes both fail here:
 * `import "./tokens.css?raw"` resolves to an EMPTY string under `css: false` (measured:
 * length 0, so the audit would score a palette of zero tokens), and `node:fs` inside a
 * test does not typecheck because `tsconfig.json` deliberately ships no `@types/node` --
 * the frontend targets the browser.
 *
 * Reading it HERE is where Node genuinely belongs: a config file already runs on Node and
 * is typed by its own tool. `define` substitutes the literal at transform time, so the
 * test stays browser-shaped and the palette has exactly one source of truth on disk.
 */
const TOKENS_CSS = readFileSync(
  fileURLToPath(new URL("./src/tokens.css", import.meta.url)),
  "utf8",
);

export default defineConfig({
  plugins: [react()],
  define: { __TOKENS_CSS__: JSON.stringify(TOKENS_CSS) },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // Component tests assert the accessibility tree, not paint, so parsing stylesheets
    // would be cost with no signal. `contrast.test.ts` needs the token TEXT instead, and
    // gets it through `__TOKENS_CSS__` below rather than by relaxing this.
    css: false,
  },
});
