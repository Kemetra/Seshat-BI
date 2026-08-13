/** Build the exact scoped and alias tarballs handed to the publish jobs. */

import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputFlag = process.argv.indexOf("--output");
if (outputFlag < 0 || !process.argv[outputFlag + 1]) {
  throw new Error("usage: node npm/stage-release-packages.js --output <directory>");
}

const requestedOutput = process.argv[outputFlag + 1];
const output = isAbsolute(requestedOutput)
  ? requestedOutput
  : resolve(repoRoot, requestedOutput);
const scopedOutput = join(output, "scoped");
const aliasOutput = join(output, "alias");

rmSync(output, { recursive: true, force: true });
mkdirSync(scopedOutput, { recursive: true });
mkdirSync(aliasOutput, { recursive: true });

const rootManifest = JSON.parse(readFileSync(join(repoRoot, "package.json"), "utf8"));
const version = rootManifest.version;

execFileSync("npm", ["test"], {
  cwd: repoRoot,
  stdio: "inherit",
  shell: process.platform === "win32",
});
execFileSync("npm", ["pack", "--pack-destination", scopedOutput], {
  cwd: repoRoot,
  stdio: "inherit",
  shell: process.platform === "win32",
});

const aliasWorkspace = mkdtempSync(join(tmpdir(), "seshat-npm-alias-"));
try {
  cpSync(join(repoRoot, "npm", "alias"), aliasWorkspace, { recursive: true });
  const aliasManifestPath = join(aliasWorkspace, "package.json");
  const aliasManifest = JSON.parse(readFileSync(aliasManifestPath, "utf8"));
  aliasManifest.version = version;
  aliasManifest.dependencies["@kemetra/seshat-bi"] = version;
  writeFileSync(aliasManifestPath, `${JSON.stringify(aliasManifest, null, 2)}\n`);
  execFileSync("npm", ["pack", "--pack-destination", aliasOutput], {
    cwd: aliasWorkspace,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
} finally {
  rmSync(aliasWorkspace, { recursive: true, force: true });
}

console.log(`staged npm release packages for ${version} in ${output}`);
