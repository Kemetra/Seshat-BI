/**
 * @kemetra/seshat-bi — programmatic access to the packaged Seshat BI skills bundle.
 *
 * This package ships CONTENT, not a runtime: the same generated Claude Code
 * bundle the repository marketplace serves (skills, commands, knowledge,
 * templates). It executes nothing and has no dependencies.
 *
 * The Seshat BI CLI (`seshat`) is a PYTHON program distributed on PyPI as
 * `seshat-bi`. npm cannot install it. The bundle's `mcp-servers.json` declares
 * a `seshat-governor` MCP server whose command is that CLI, so the governor
 * tools only work once the Python package is installed separately:
 *
 *     pipx install "seshat-bi[mcp]"
 *
 * Without it the server fails closed with a named install hint — it never
 * degrades silently or simulates a governor.
 */

import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const packageRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

/** Absolute path to the bundle directory (skills/, commands/, knowledge/, ...). */
export const bundlePath = join(
  packageRoot,
  "integrations",
  "claude-code",
  "seshat-bi",
);

/** Absolute path to the bundle's Claude plugin manifest. */
export const pluginManifestPath = join(
  bundlePath,
  ".claude-plugin",
  "plugin.json",
);

/**
 * The generated bundle manifest: the authored record of what ships, including
 * per-file digests and the source revision it was generated from.
 */
export const bundleManifest = require(join(bundlePath, "bundle-manifest.json"));

/**
 * The Python distribution that provides the `seshat` CLI. Install it separately
 * — this npm package deliberately does not shell out to pip or pipx.
 */
export const pythonDistribution = "seshat-bi";

/** The install command that enables the bundle's declared MCP server. */
export const cliInstallCommand = 'pipx install "seshat-bi[mcp]"';

export default {
  bundlePath,
  pluginManifestPath,
  bundleManifest,
  pythonDistribution,
  cliInstallCommand,
};
