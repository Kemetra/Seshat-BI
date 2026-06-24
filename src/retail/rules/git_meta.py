"""Git-metadata rules (C2, G1–G5, P1, P2)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .. import gitutil
from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

# ---------------------------------------------------------------------------
# G5 — Windows MAX_PATH discipline
# ---------------------------------------------------------------------------

MAX_REL_PATH = 200


@register("G5", "Windows MAX_PATH discipline")
def rule_g5_path_length(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for path in ctx.tracked_files:
        if len(path) > MAX_REL_PATH:
            findings.append(
                Finding(
                    rule_id="G5",
                    severity=Severity.ERROR,
                    message=(
                        f"repo-relative path is {len(path)} chars "
                        f"(> {MAX_REL_PATH}); risks Windows MAX_PATH overflow"
                    ),
                    locator=path,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# P1 — Approach-A layout
# ---------------------------------------------------------------------------

REQUIRED_PATHS = ("README.md", "warehouse/README.md", "powerbi/README.md")
PBIP_SIGNATURES = (".pbip", "definition.pbir")
PBIP_DIR_MARKERS = (".SemanticModel/", ".Report/")


def _is_pbip_signature(path: str) -> bool:
    if path.endswith(PBIP_SIGNATURES):
        return True
    return any(marker in path for marker in PBIP_DIR_MARKERS)


@register("P1", "Approach-A layout")
def rule_p1_layout(ctx: RuleContext) -> Iterable[Finding]:
    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []
    for required in REQUIRED_PATHS:
        if required not in tracked:
            findings.append(
                Finding(
                    rule_id="P1",
                    severity=Severity.ERROR,
                    message=f"required layout path is missing: {required}",
                    locator=required,
                )
            )
    for path in ctx.tracked_files:
        # Committed test fixtures (e.g. tests/fixtures/golden_pbip/*.pbip and any
        # test *.sql) are not the live model and must not be forced under
        # powerbi/ or warehouse/. Skip them before the production-layout checks.
        if is_test_path(path):
            continue
        if _is_pbip_signature(path) and not path.startswith("powerbi/"):
            findings.append(
                Finding(
                    rule_id="P1",
                    severity=Severity.ERROR,
                    message="PBIP artifact must live under powerbi/",
                    locator=path,
                )
            )
        if path.endswith(".sql") and not path.startswith("warehouse/"):
            findings.append(
                Finding(
                    rule_id="P1",
                    severity=Severity.ERROR,
                    message="*.sql must live under warehouse/",
                    locator=path,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# G1 — .gitignore correctness
# ---------------------------------------------------------------------------

REQUIRED_IGNORES = (
    "**/.pbi/localSettings.json",
    "**/.pbi/cache.abf",
    ".env",
)
# synthesized PBIP definition paths that must NOT be ignored
DEFINITION_PROBE_PATHS = (
    "powerbi/Sales.SemanticModel/definition/model.tmdl",
    "powerbi/Sales.Report/definition/report.json",
)


@register("G1", ".gitignore correctness")
def rule_g1_gitignore_correctness(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    gitignore = ctx.repo_root / ".gitignore"
    lines = (
        {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
        if gitignore.exists()
        else set()
    )
    for required in REQUIRED_IGNORES:
        if required not in lines:
            findings.append(
                Finding(
                    rule_id="G1",
                    severity=Severity.ERROR,
                    message=f".gitignore must contain '{required}'",
                    locator=".gitignore",
                )
            )
    for probe in DEFINITION_PROBE_PATHS:
        if gitutil.git_check_ignore(ctx.repo_root, probe):
            findings.append(
                Finding(
                    rule_id="G1",
                    severity=Severity.ERROR,
                    message=(
                        "a .gitignore pattern ignores a PBIP definition/ path "
                        "(the model must never be ignored)"
                    ),
                    locator=probe,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# G2 — definition artifacts committed
# ---------------------------------------------------------------------------

FORBIDDEN_TRACKED = (".pbi/localSettings.json", ".pbi/cache.abf")


@register("G2", "definition artifacts committed")
def rule_g2_definition_committed(ctx: RuleContext) -> Iterable[Finding]:
    # Exempt committed test fixtures: tests/fixtures/**.pbip / .Report / .tmdl
    # are NOT the live model. Without this filter G2 counts them as a real PBIP
    # project, emits zero findings, and silently passes as if a model were
    # verified — the exact false assurance spec §5.5/§11 forbids. With the
    # filter, a repo whose only PBIP-shaped files are fixtures correctly falls
    # into the empty-case INFO branch below ("no PBIP project present").
    pbip_paths = [
        p for p in ctx.tracked_files if _is_pbip_signature(p) and not is_test_path(p)
    ]
    if not pbip_paths:
        return [
            Finding(
                rule_id="G2",
                severity=Severity.INFO,
                message="no PBIP project present",
                locator=".",
            )
        ]
    findings: list[Finding] = []
    for path in ctx.tracked_files:
        if path.endswith(FORBIDDEN_TRACKED):
            findings.append(
                Finding(
                    rule_id="G2",
                    severity=Severity.ERROR,
                    message="Desktop-local PBIP file must not be tracked",
                    locator=path,
                )
            )
    for path in pbip_paths:
        if gitutil.git_check_ignore(ctx.repo_root, path):
            findings.append(
                Finding(
                    rule_id="G2",
                    severity=Severity.ERROR,
                    message="tracked PBIP artifact is also gitignored",
                    locator=path,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# P2 — commit-message convention
# ---------------------------------------------------------------------------

SUBJECT_RE = re.compile(r"^(feat|fix|refactor|docs|chore): .+")
# Local-fallback range when no --commit-range is supplied. On a repo with fewer
# than 20 commits git rejects HEAD~20; the guard below turns that into a clean
# P2 ERROR finding (not a no-op). CI uses fetch-depth: 0 (full history) and
# normally supplies an explicit --commit-range, so this fallback is local-only.
DEFAULT_RANGE = "HEAD~20..HEAD"


@register("P2", "commit-message convention")
def rule_p2_commit_subjects(ctx: RuleContext) -> Iterable[Finding]:
    # Source the subjects to validate from the contract-v2 invocation fields:
    #   commit-msg-hook mode -> the single incoming message;
    #   CI mode             -> every subject in the supplied commit range,
    #                          used VERBATIM (e.g. "origin/main..HEAD");
    #   local fallback       -> the last DEFAULT_RANGE commits.
    if ctx.commit_message is not None:
        subjects = [ctx.commit_message.splitlines()[0] if ctx.commit_message else ""]
    else:
        # --commit-range is a full revision range; never append "..HEAD".
        range_expr = ctx.commit_range if ctx.commit_range is not None else DEFAULT_RANGE
        try:
            subjects = gitutil.git_log_subjects(ctx.repo_root, range_expr)
        except RuntimeError as exc:
            # A malformed/empty range must surface as a clean ERROR Finding, not
            # a traceback (the runner does not wrap rules in try/except).
            return [
                Finding(
                    rule_id="P2",
                    severity=Severity.ERROR,
                    message=f"could not read commit range {range_expr!r}: {exc}",
                    locator=range_expr,
                )
            ]
    findings: list[Finding] = []
    for subject in subjects:
        if not SUBJECT_RE.match(subject):
            findings.append(
                Finding(
                    rule_id="P2",
                    severity=Severity.ERROR,
                    message=(
                        "commit subject must match "
                        "'<type>: <desc>' (feat|fix|refactor|docs|chore)"
                    ),
                    locator=subject,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# C2 — no committed secrets
# ---------------------------------------------------------------------------

# A real DigitalOcean endpoint: a concrete subdomain label (alnum start, then
# alnum/hyphen) directly before `.db.ondigitalocean.com`. `>` from an
# angle-bracket placeholder cannot sit in the label class, so
# `<your-db-host>.db.ondigitalocean.com` does NOT match.
#
# ReDoS-safe: the label run is BOUNDED ({0,253}, the DNS host-name max) rather
# than an unbounded `*`. An unbounded `[A-Za-z0-9-]*` directly before the literal
# can backtrack catastrophically on a long alnum/hyphen run that is then followed
# by `.db.ondigitalocean.com`; bounding the quantifier caps backtracking to a
# constant per start position, so the match is O(n) over the line. Real subdomain
# labels are far shorter than 253, so the bound never under-matches a true
# endpoint (and the `>`-placeholder exclusion is unchanged — `>` is still outside
# the label class).
DO_ENDPOINT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,253}\.db\.ondigitalocean\.com")
CONN_URI_RE = re.compile(r"postgres(?:ql)?://[^@\s]+@")
REQUIRED_ENV_KEYS = (
    "ANALYTICS_DB_HOST",
    "ANALYTICS_DB_PORT",
    "ANALYTICS_DB_NAME",
    "ANALYTICS_DB_USER",
    "ANALYTICS_DB_PASSWORD",
    "ANALYTICS_DB_SSLMODE",
)
MUST_BE_EMPTY = (
    "ANALYTICS_DB_HOST",
    "ANALYTICS_DB_NAME",
    "ANALYTICS_DB_USER",
    "ANALYTICS_DB_PASSWORD",
)


# Path prefixes excluded from the C2 CONTENT regex scan. tests/ holds fixtures
# that intentionally contain secret-LOOKING literals to exercise the scanner,
# and .superpowers/ holds SDD scratch/reports that quote those fixtures; neither
# is tracked source that could leak a real secret. (Scope: content scan only —
# the .env and .env.example sub-checks are unaffected.)
_C2_SCAN_EXCLUDED_PREFIXES = ("docs/", "tests/", ".superpowers/")


def _scan_excluded(path: str) -> bool:
    return path.startswith(_C2_SCAN_EXCLUDED_PREFIXES) or path.endswith(".example")


def _check_env_file(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    if ".env" in ctx.tracked_files:
        findings.append(
            Finding(
                rule_id="C2",
                severity=Severity.ERROR,
                message=".env must never be tracked",
                locator=".env",
            )
        )
    elif not gitutil.git_check_ignore(ctx.repo_root, ".env"):
        findings.append(
            Finding(
                rule_id="C2",
                severity=Severity.ERROR,
                message=".env must be gitignored",
                locator=".gitignore",
            )
        )
    return findings


def _check_env_example(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    example = ctx.repo_root / ".env.example"
    if not example.exists():
        return [
            Finding(
                rule_id="C2",
                severity=Severity.ERROR,
                message=".env.example is missing",
                locator=".env.example",
            )
        ]
    pairs: dict[str, str] = {}
    for line in example.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pairs[key.strip()] = value.strip()
    for key in REQUIRED_ENV_KEYS:
        if key not in pairs:
            findings.append(
                Finding(
                    rule_id="C2",
                    severity=Severity.ERROR,
                    message=f".env.example missing key {key}",
                    locator=".env.example",
                )
            )
    for key in MUST_BE_EMPTY:
        if pairs.get(key):
            findings.append(
                Finding(
                    rule_id="C2",
                    severity=Severity.ERROR,
                    message=f".env.example {key} must be empty (no committed value)",
                    locator=".env.example",
                )
            )
    return findings


def _scan_contents(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for path in ctx.tracked_files:
        if _scan_excluded(path):
            continue
        full = ctx.repo_root / path
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            # DO_ENDPOINT_RE ([A-Za-z0-9][A-Za-z0-9-]*\.db\.ondigitalocean\.com)
            # backtracks O(n^2) on a long alnum/hyphen run (~minutes on a 200k-char
            # minified line). stdlib re has no possessive quantifiers, so gate it
            # behind an O(n) substring check: any real endpoint MUST contain this
            # literal, so the prefilter is a necessary condition — behavior is
            # identical, only the pathological scan is skipped. CONN_URI_RE's
            # [^@\s]+@ is already linear (the class excludes @), so it runs as-is.
            do_hit = ".db.ondigitalocean.com" in line and DO_ENDPOINT_RE.search(line)
            if CONN_URI_RE.search(line) or do_hit:
                findings.append(
                    Finding(
                        rule_id="C2",
                        severity=Severity.ERROR,
                        message="possible committed connection string / secret",
                        locator=f"{path}:{lineno}",
                    )
                )
    return findings


@register("C2", "no committed secrets")
def rule_c2_no_committed_secrets(ctx: RuleContext) -> Iterable[Finding]:
    return [
        *_check_env_file(ctx),
        *_check_env_example(ctx),
        *_scan_contents(ctx),
    ]


# ---------------------------------------------------------------------------
# G3 — UTF-8 without BOM
# ---------------------------------------------------------------------------

_UTF8_BOM = b"\xef\xbb\xbf"
_G3_SUFFIXES = (".tmdl", ".pbir", ".json", ".pbism")


def _read_leading_bytes(path: Path, count: int = 3) -> bytes:
    """Return up to ``count`` leading bytes of ``path``.

    Reads in binary mode on purpose: a text open with ``encoding="utf-8-sig"``
    would strip the BOM that G3 exists to detect. A file shorter than ``count``
    simply yields fewer bytes (no error, comparison is False).
    """
    with path.open("rb") as fh:
        return fh.read(count)


@register("G3", "UTF-8 without BOM")
def rule_g3_no_bom(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any committed TMDL/PBIR/JSON/PBISM file beginning with a UTF-8 BOM."""
    for rel in ctx.tracked_files:
        # Exempt committed test fixtures (consistency with G2 and the file-
        # scanning rules): a tests/ BOM fixture, once added, is intentional and
        # must not false-positive. Latent today (no such fixture tracked yet).
        if is_test_path(rel):
            continue
        if not rel.lower().endswith(_G3_SUFFIXES):
            continue
        if _read_leading_bytes(ctx.repo_root / rel) == _UTF8_BOM:
            yield Finding(
                rule_id="G3",
                severity=Severity.ERROR,
                message=(
                    f"File starts with a UTF-8 BOM; save as UTF-8 without BOM: {rel}"
                ),
                locator=rel,
            )


# ---------------------------------------------------------------------------
# G4 — .gitattributes EOL policy (MUST-CONTAIN subset)
# ---------------------------------------------------------------------------

# Required (glob -> required attribute token).
# Exact first-token match, subset semantics.
_G4_REQUIRED: tuple[tuple[str, str], ...] = (
    ("*.tmdl", "eol=crlf"),
    ("*.pbir", "eol=crlf"),
    ("*.pbism", "eol=crlf"),
    ("*.json", "eol=crlf"),
    ("*.sql", "eol=lf"),
    ("*.md", "eol=lf"),
    ("*.py", "eol=lf"),
    ("*.pbix", "binary"),
    ("*.abf", "binary"),
    ("*.png", "binary"),
)


@register("G4", ".gitattributes EOL policy")
def check_gitattributes_eol(ctx: RuleContext) -> Iterable[Finding]:
    """G4: each REQUIRED glob in .gitattributes must carry its eol/binary token.

    Subset (MUST-CONTAIN) check: extra benign entries are permitted. Matching is
    by exact first-token equality, never glob expansion, so the `* text=auto`
    catch-all does not satisfy any required glob.
    """
    path = ctx.repo_root / ".gitattributes"
    # Index: glob token -> (1-based line number, set of remaining tokens on that line).
    declared: dict[str, tuple[int, set[str]]] = {}
    if path.exists():
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            glob = tokens[0]
            declared[glob] = (lineno, set(tokens[1:]))

    findings: list[Finding] = []
    for glob, required_token in _G4_REQUIRED:
        entry = declared.get(glob)
        if entry is None:
            findings.append(
                Finding(
                    rule_id="G4",
                    severity=Severity.ERROR,
                    message=(
                        f"{glob} missing required attribute"
                        f" {required_token} in .gitattributes"
                    ),
                    locator=".gitattributes",
                )
            )
            continue
        lineno, attr_tokens = entry
        if required_token not in attr_tokens:
            findings.append(
                Finding(
                    rule_id="G4",
                    severity=Severity.ERROR,
                    message=f"{glob} must declare {required_token} in .gitattributes",
                    locator=f".gitattributes:{lineno}",
                )
            )
    return findings
