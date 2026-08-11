import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Studio's browser build.
 *
 * `outDir` is `dist`, which the documented build command copies into
 * `src/seshat/studio/static/` so hatchling ships it inside the wheel (FR-005). The
 * static directory sits INSIDE an already-declared wheel package, so no force-include
 * is needed -- and a force-include pointing at a not-yet-built directory would break
 * `pip install` for everyone.
 *
 * FR-033 forbids remote fonts, scripts, images, and analytics, so:
 *  - `assetsInlineLimit: 0` keeps assets as local files rather than inlining
 *    unpredictably, making the "no remote reference" test able to see them all;
 *  - no CDN plugin, no external font import, no analytics;
 *  - `base: "./"` emits RELATIVE asset URLs, so the bundle works from whatever
 *    loopback port the OS assigns without a rebuild.
 */
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 0,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Stable, content-hashed names so a stale browser cache cannot serve a
        // mismatched bundle after an upgrade.
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  server: {
    // Development only. The packaged app is served by the Python process on an
    // OS-assigned loopback port; this proxy just lets `npm run dev` talk to it.
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8931",
        changeOrigin: false,
      },
    },
  },
});
