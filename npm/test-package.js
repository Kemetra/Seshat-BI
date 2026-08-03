/**
 * Packaging guarantee test for @kemetra/seshat-bi.
 *
 * The risk this sits on: `files` in package.json is a WHITELIST. A bundle
 * subdirectory that is added later but never listed simply does not ship, and
 * nothing fails — the package publishes successfully and is silently
 * incomplete. Asserting the contents of `files` would just restate the config;
 * this asks `npm pack` what the REAL tarball contains and checks that against
 * the bundle on disk, which is an independent oracle.
 *
 * Run: node npm/test-package.js   (or: npm test)
 */

import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const BUNDLE_REL = "integrations/claude-code/seshat-bi";

const failures = [];
const check = (label, ok, detail = "") => {
  if (ok) {
    console.log(`  [OK]   ${label}`);
  } else {
    console.log(`  [FAIL] ${label}${detail ? ` -- ${detail}` : ""}`);
    failures.push(label);
  }
};

// --- what npm would actually ship -------------------------------------------
const packed = JSON.parse(
  execFileSync("npm", ["pack", "--dry-run", "--json"], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
    shell: process.platform === "win32",
  }),
);
const shipped = new Set(packed[0].files.map((f) => f.path.replace(/\\/g, "/")));

// --- every bundle file on disk must be in the tarball ------------------------
const walk = (dir, acc = []) => {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, acc);
    else acc.push(full.replace(/\\/g, "/").slice(repoRoot.length + 1));
  }
  return acc;
};

const onDisk = walk(join(repoRoot, BUNDLE_REL));
const missing = onDisk.filter((f) => !shipped.has(f));
check(
  `every bundle file ships (${onDisk.length} on disk)`,
  missing.length === 0,
  missing.length ? `${missing.length} missing, e.g. ${missing[0]}` : "",
);

// --- the load-bearing entries, named explicitly ------------------------------
for (const required of [
  "package.json",
  "npm/index.js",
  "npm/README.md",
  "LICENSE",
  `${BUNDLE_REL}/bundle-manifest.json`,
  `${BUNDLE_REL}/.claude-plugin/plugin.json`,
  `${BUNDLE_REL}/mcp-servers.json`,
]) {
  check(`ships ${required}`, shipped.has(required));
}

// --- skills are the product; a bundle that lost them is not publishable ------
const skillDirs = readdirSync(join(repoRoot, BUNDLE_REL, "skills"), {
  withFileTypes: true,
}).filter((d) => d.isDirectory());
check(`bundle carries skills (${skillDirs.length})`, skillDirs.length >= 21);
check(
  "every skill ships its SKILL.md",
  skillDirs.every((d) => shipped.has(`${BUNDLE_REL}/skills/${d.name}/SKILL.md`)),
);

// --- version parity: npm must match the Python release and the bundle --------
const pkg = JSON.parse(readFileSync(join(repoRoot, "package.json"), "utf8"));
const pluginVersion = JSON.parse(
  readFileSync(join(repoRoot, BUNDLE_REL, ".claude-plugin/plugin.json"), "utf8"),
).version;
const pyprojectVersion = readFileSync(join(repoRoot, "pyproject.toml"), "utf8")
  .match(/^version\s*=\s*"([^"]+)"/m)?.[1];

check(
  `npm version matches plugin manifest (${pkg.version} vs ${pluginVersion})`,
  pkg.version === pluginVersion,
);
check(
  `npm version matches pyproject (${pkg.version} vs ${pyprojectVersion})`,
  pkg.version === pyprojectVersion,
);

// --- the package must stay content-only --------------------------------------
check("no runtime dependencies", !pkg.dependencies);
check(
  "no install scripts",
  !["preinstall", "install", "postinstall"].some((s) => pkg.scripts?.[s]),
);

console.log(
  failures.length
    ? `\n[FAIL] ${failures.length} packaging check(s) failed.`
    : `\n[DONE] all packaging checks passed (${shipped.size} files).`,
);
process.exit(failures.length ? 1 : 0);
