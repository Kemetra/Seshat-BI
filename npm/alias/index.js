/**
 * seshat-bi — alias for @kemetra/seshat-bi.
 *
 * This package holds the unscoped name and forwards to the canonical scoped
 * package, which carries the actual bundle. Everything exported by
 * `@kemetra/seshat-bi` is re-exported here, so `import ... from "seshat-bi"`
 * behaves identically.
 *
 * Prefer depending on `@kemetra/seshat-bi` directly. This alias exists so the
 * unscoped name resolves to the real package rather than being unclaimed.
 *
 * NOTE: the `seshat` CLI is a PYTHON program on PyPI (`seshat-bi`), which npm
 * cannot install. This npm name and that PyPI name are different artifacts
 * that happen to share a string. For the CLI:
 *
 *     pipx install "seshat-bi[mcp]"
 */

export * from "@kemetra/seshat-bi";
export { default } from "@kemetra/seshat-bi";
