"""Git-metadata rules (C2, G1–G5, P1, P2)."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from pathlib import Path

from .. import gitutil
from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register


def _absent_findings(
    required: Iterable[str],
    is_present: Callable[[str], bool],
    make_finding: Callable[[str], Finding],
) -> list[Finding]:
    """One ERROR Finding per required item that is not present.

    The shared shape behind the several "every required X must exist" checks
    (P1 layout paths, G1 .gitignore entries, C2 .env.example keys): iterate the
    required collection, keep the absent ones, and build each rule's own
    Finding. Callers supply the presence test and the Finding factory so the
    rule_id / message / locator stay per-rule.
    """
    return [make_finding(item) for item in required if not is_present(item)]


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


def _missing_required_layout(tracked: set[str]) -> list[Finding]:
    return _absent_findings(
        REQUIRED_PATHS,
        lambda required: required in tracked,
        lambda required: Finding(
            rule_id="P1",
            severity=Severity.ERROR,
            message=f"required layout path is missing: {required}",
            locator=required,
        ),
    )


def _pbip_placement_finding(path: str) -> Finding | None:
    if _is_pbip_signature(path) and not path.startswith("powerbi/"):
        return Finding(
            rule_id="P1",
            severity=Severity.ERROR,
            message="PBIP artifact must live under powerbi/",
            locator=path,
        )
    return None


def _sql_placement_finding(path: str) -> Finding | None:
    if path.endswith(".sql") and not path.startswith("warehouse/"):
        return Finding(
            rule_id="P1",
            severity=Severity.ERROR,
            message="*.sql must live under warehouse/",
            locator=path,
        )
    return None


@register("P1", "Approach-A layout")
def rule_p1_layout(ctx: RuleContext) -> Iterable[Finding]:
    findings = _missing_required_layout(set(ctx.tracked_files))
    for path in ctx.tracked_files:
        # Committed test fixtures (e.g. tests/fixtures/golden_pbip/*.pbip and any
        # test *.sql) are not the live model and must not be forced under
        # powerbi/ or warehouse/. Skip them before the production-layout checks.
        if is_test_path(path):
            continue
        # A single path can trip both checks (a PBIP-signature *.sql outside both
        # trees) -> emit both, PBIP finding first, matching the original order.
        for finding in (_pbip_placement_finding(path), _sql_placement_finding(path)):
            if finding is not None:
                findings.append(finding)
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


def _missing_required_ignores(lines: set[str]) -> list[Finding]:
    return _absent_findings(
        REQUIRED_IGNORES,
        lambda required: required in lines,
        lambda required: Finding(
            rule_id="G1",
            severity=Severity.ERROR,
            message=f".gitignore must contain '{required}'",
            locator=".gitignore",
        ),
    )


def _ignored_definition_findings(ctx: RuleContext) -> list[Finding]:
    return [
        Finding(
            rule_id="G1",
            severity=Severity.ERROR,
            message=(
                "a .gitignore pattern ignores a PBIP definition/ path "
                "(the model must never be ignored)"
            ),
            locator=probe,
        )
        for probe in DEFINITION_PROBE_PATHS
        if gitutil.git_check_ignore(ctx.repo_root, probe)
    ]


@register("G1", ".gitignore correctness")
def rule_g1_gitignore_correctness(ctx: RuleContext) -> Iterable[Finding]:
    gitignore = ctx.repo_root / ".gitignore"
    lines = (
        {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
        if gitignore.exists()
        else set()
    )
    return [*_missing_required_ignores(lines), *_ignored_definition_findings(ctx)]


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
    return [
        *_forbidden_tracked_findings(ctx),
        *_gitignored_pbip_findings(ctx, pbip_paths),
    ]


def _forbidden_tracked_findings(ctx: RuleContext) -> list[Finding]:
    return [
        Finding(
            rule_id="G2",
            severity=Severity.ERROR,
            message="Desktop-local PBIP file must not be tracked",
            locator=path,
        )
        for path in ctx.tracked_files
        if path.endswith(FORBIDDEN_TRACKED)
    ]


def _gitignored_pbip_findings(ctx: RuleContext, pbip_paths: list[str]) -> list[Finding]:
    return [
        Finding(
            rule_id="G2",
            severity=Severity.ERROR,
            message="tracked PBIP artifact is also gitignored",
            locator=path,
        )
        for path in pbip_paths
        if gitutil.git_check_ignore(ctx.repo_root, path)
    ]


# ---------------------------------------------------------------------------
# P2 — commit-message convention
# ---------------------------------------------------------------------------

# Allowed commit types for HUMAN-authored subjects: the original core set plus
# the standard Conventional-Commits types and the project-specific `brand` type
# (brand / visual-identity assets). A `type(scope):` parenthesized scope is
# REJECTED -- governance rule P2 is deliberately scope-free (use `docs:` not
# `docs(018):`).
#
# AUTOMATION EXEMPTION: a subject carrying a leading `[name]` prefix
# (e.g. `[codex]`, `[bot]`) is an automated/tool-generated commit whose subject
# format the kit does not control (it arrives via a squash merge of a bot PR).
# Such subjects are accepted as-is, since enforcing the human convention on a
# machine-written subject is out of the author's hands. Human subjects (no
# bracket prefix) must still be `<type>: <desc>`, scope-free.
# See docs/decisions/0012-p2-commit-types.md.
_P2_TYPES = (
    "feat",
    "fix",
    "refactor",
    "docs",
    "chore",
    "build",
    "ci",
    "perf",
    "test",
    "style",
    "revert",
    "brand",
)
_BOT_PREFIX_RE = re.compile(r"^\[[A-Za-z0-9_-]+\] ")
SUBJECT_RE = re.compile(r"^(?:" + "|".join(_P2_TYPES) + r"): .+")
# Local-fallback range when neither --commit-range nor a commit-msg hook message
# is supplied (a bare `retail check`). Scoped to the CURRENT/incoming commit only
# (HEAD~1..HEAD) so a normal local check is green whenever the current change is
# compliant, and is never tripped by aged-out non-conforming history (#112). On a
# single-commit repo git rejects HEAD~1 (rc 128); the except (RuntimeError,
# ValueError) branch below turns that into a clean P2 ERROR Finding (not a
# traceback), exactly as the old HEAD~20 default did. CI supplies an explicit
# --commit-range (merge-base(origin/main, HEAD)..HEAD) and the commit-msg hook
# uses ctx.commit_message, so BOTH bypass this fallback -- new-commit P2
# enforcement is unaffected.
DEFAULT_RANGE = "HEAD~1..HEAD"


def _load_subjects(ctx: RuleContext) -> tuple[list[str], list[Finding]]:
    """Resolve the commit subjects to validate for the contract-v2 invocation.

    Returns ``(subjects, findings)``: on a malformed/unsafe/empty range the
    subjects list is empty and ``findings`` carries the single ERROR (so no
    subject validation runs), mirroring the original short-circuit ``return``.
    """
    #   commit-msg-hook mode -> the single incoming message;
    #   CI mode             -> every subject in the supplied commit range,
    #                          used VERBATIM (e.g. "origin/main..HEAD");
    #   local fallback       -> just the current/incoming commit (DEFAULT_RANGE).
    if ctx.commit_message is not None:
        return ([ctx.commit_message.splitlines()[0] if ctx.commit_message else ""], [])
    # A freshly `git init`-ed workspace has no HEAD yet. It is a valid
    # first-success state, so there is no commit subject for P2 to judge. Keep the
    # normal error posture for non-repositories and malformed explicit ranges.
    if ctx.commit_range is None:
        inside_work_tree = ""
        try:
            inside_work_tree = gitutil.git_output(
                ctx.repo_root, "rev-parse", "--is-inside-work-tree"
            ).strip()
            gitutil.git_output(ctx.repo_root, "rev-parse", "--verify", "HEAD")
        except RuntimeError:
            if inside_work_tree == "true":
                return ([], [])
    # --commit-range is a full revision range; never append "..HEAD".
    range_expr = ctx.commit_range if ctx.commit_range is not None else DEFAULT_RANGE
    try:
        return (gitutil.git_log_subjects(ctx.repo_root, range_expr), [])
    except (RuntimeError, ValueError) as exc:
        # A malformed/unsafe/empty range must surface as a clean ERROR Finding,
        # not a traceback (the runner does not wrap rules in try/except).
        # ValueError = rejected by validate_commit_range (option injection);
        # RuntimeError = git rejected a safe-shaped range.
        return (
            [],
            [
                Finding(
                    rule_id="P2",
                    severity=Severity.ERROR,
                    message=f"could not read commit range {range_expr!r}: {exc}",
                    locator=range_expr,
                )
            ],
        )


def _subject_ok(subject: str) -> bool:
    # Automated/tool-generated subjects (leading `[name]` prefix) are exempt
    # from the human convention -- the kit does not control their format.
    return bool(_BOT_PREFIX_RE.match(subject)) or bool(SUBJECT_RE.match(subject))


def _invalid_subject_findings(subjects: list[str]) -> list[Finding]:
    return [
        Finding(
            rule_id="P2",
            severity=Severity.ERROR,
            message=(
                "commit subject must match '<type>: <desc>' "
                "(" + "|".join(_P2_TYPES) + "); "
                "scopes are not allowed (use 'docs:' not 'docs(018):'); "
                "automated '[bot] ...' subjects are exempt"
            ),
            locator=subject,
        )
        for subject in subjects
        if not _subject_ok(subject)
    ]


@register("P2", "commit-message convention")
def rule_p2_commit_subjects(ctx: RuleContext) -> Iterable[Finding]:
    # Source the subjects to validate from the contract-v2 invocation fields.
    subjects, load_findings = _load_subjects(ctx)
    return [*load_findings, *_invalid_subject_findings(subjects)]


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
# A DigitalOcean managed-database CLUSTER SLUG has the shape
# `db-<engine>-<region-letters><digit>-<numeric-id>` (a concrete example is a
# `db-` prefix, an engine token, a region label ending in a digit, then a run of
# digits). It is NOT a secret on its own (it grants no access and hides the full
# FQDN), but it IS real connection context the repo's hard rule ("never write real
# values into tracked files") forbids -- and the audit found it committed in 8
# files, invisible to the FQDN/URI patterns above. The pattern is anchored on the
# engine token + `<region-letters><digit>` + trailing numeric cluster id, so
# ordinary hyphenated tokens (table names use `_`; `dim-`/`fct-` never carry a
# trailing `-<digits>`) do not match, and the `<...>` angle-bracket placeholder
# cannot appear inside the character class, so a documented placeholder such as
# `db-<engine>-<region>-<id>` does NOT match. (This very comment is deliberately
# written to describe the shape without embedding a matching literal.)
DO_CLUSTER_SLUG_RE = re.compile(r"\bdb-[a-z]{2,}-[a-z]{2,}\d-\d{3,}\b")

# Task 11 (R4/C2 extension) — catch three more committed-secret SHAPES the
# Postgres-only patterns above are blind to: an ODBC keyword string carrying a
# real credential value for either of two ODBC keywords (the connection
# password keyword and the connection user-id keyword), a MySQL connection
# URI, and a Snowflake account-plus-password kwargs pair. Each VALUE class
# deliberately excludes:
#   * an angle-bracket-wrapped token (the existing documented-placeholder
#     exemption),
#   * a curly brace (an f-string/format-string interpolation token -- SOURCE
#     CODE building the string, not a committed secret; this is what keeps
#     this very module's own dialect.py resolve_config() bodies from self-
#     tripping the scanner they extend), and
#   * the ODBC keyword separator / whitespace / a slash (so PROSE describing
#     "keyword A or keyword B" together, as in this very comment, cannot
#     itself look like a real assigned value).
# so a real literal value (letters/digits/most punctuation) still matches,
# while the placeholder/interpolation/prose shapes do not. (This comment block
# is deliberately written without the two ODBC keywords' literal `KEYWORD=`
# forms appearing back to back, for the same reason the DO_CLUSTER_SLUG_RE
# comment above avoids embedding a matching literal.)
ODBC_SECRET_RE = re.compile(r"\b(?:PWD|UID)=[^;\s{}<>/]+")
# The scheme is assembled from parts (mirroring validate.py's postgres scheme
# split) so this source file never itself contains the full scheme-then-
# userinfo-then-at-sign literal shape the pattern below exists to catch --
# angle brackets are excluded from the userinfo class so a documented
# placeholder (a MySQL URI with bracketed user/password/host tokens) does not
# match either.
_MYSQL_SCHEME = "mysql" + ":" + "//"
MYSQL_URI_RE = re.compile(re.escape(_MYSQL_SCHEME) + r"[^@\s<>]+@")

# Snowflake kwargs pair: `account=`/`account:` (optionally quoted key) with a
# REAL value, together with a `password=`/`password:` REAL value anywhere on
# the same line -- the pairing is what makes it connection context (a bare
# `account=` alone is not flagged; it grants no access on its own). A regex
# alone over-matches Python source that BUILDS such a dict from env vars (e.g.
# `config["account"] = env.get("ANALYTICS_DB_ACCOUNT")` -- the "value" here is
# a variable reference, not a literal), so a value is accepted only when it is
# a quoted string OR an unquoted token NOT immediately followed by `.` or `(`
# in the source (which would mark it as a name/attribute/call reference).
_SNOWFLAKE_KV_RE = re.compile(
    r"[\"']?(account|password)[\"']?\s*[:=]\s*([\"']?)([^,;\s\"'{}()<>]*)",
    re.IGNORECASE,
)


def _snowflake_kv_is_real(quote: str, value: str, line: str, end_pos: int) -> bool:
    if not value:
        return False
    is_unquoted = not quote
    has_next_char = end_pos < len(line)
    next_is_ref = has_next_char and line[end_pos] in ".("
    if is_unquoted and next_is_ref:
        return False  # unquoted + followed by '.'/'(' -> a name/call reference
    return True


def _has_snowflake_secret_pair(line: str) -> bool:
    seen: dict[str, bool] = {}
    for m in _SNOWFLAKE_KV_RE.finditer(line):
        key, quote, value = m.group(1).lower(), m.group(2), m.group(3)
        if _snowflake_kv_is_real(quote, value, line, m.end(3)):
            seen[key] = True
    return seen.get("account", False) and seen.get("password", False)


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
# that intentionally contain secret-LOOKING literals to exercise the scanner;
# docs/superpowers/ and .superpowers/ hold SDD scratch/reports/plans that QUOTE
# those fixtures (e.g. a sample postgres connection URL inside a plan's code
# block); none is tracked source that could leak a real secret.
# Audit 2026-06-26 #8: the exclusion was narrowed from all of docs/ to
# docs/superpowers/ so REAL operational docs/runbooks (docs/operations/,
# docs/architecture/, …) ARE scanned -- a leaked DSN in a runbook was the audit's
# concern and was previously invisible. (Scope: content scan only — the .env and
# .env.example sub-checks are unaffected.)
_C2_SCAN_EXCLUDED_PREFIXES = ("docs/superpowers/", "tests/", ".superpowers/")


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


def _parse_env_pairs(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines of a .env-style file, skipping comments/blanks."""
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pairs[key.strip()] = value.strip()
    return pairs


def _missing_required_keys(pairs: dict[str, str]) -> list[Finding]:
    return _absent_findings(
        REQUIRED_ENV_KEYS,
        lambda key: key in pairs,
        lambda key: Finding(
            rule_id="C2",
            severity=Severity.ERROR,
            message=f".env.example missing key {key}",
            locator=".env.example",
        ),
    )


def _nonempty_must_be_empty(pairs: dict[str, str]) -> list[Finding]:
    return [
        Finding(
            rule_id="C2",
            severity=Severity.ERROR,
            message=f".env.example {key} must be empty (no committed value)",
            locator=".env.example",
        )
        for key in MUST_BE_EMPTY
        if pairs.get(key)
    ]


def _check_env_example(ctx: RuleContext) -> list[Finding]:
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
    pairs = _parse_env_pairs(example.read_text(encoding="utf-8"))
    return [*_missing_required_keys(pairs), *_nonempty_must_be_empty(pairs)]


def _scan_line_for_secret(line: str) -> bool:
    """True if ``line`` carries a committed connection string / secret shape.

    Factored out of ``_scan_contents`` (Task 11) so the multi-engine patterns
    (the ODBC credential keywords, a MySQL connection URI, a Snowflake
    account-plus-password pair) share one tested seam with the original
    Postgres URI / DigitalOcean endpoint checks.
    Excludes the DO cluster-slug shape, which is reported as a SEPARATE, less
    severe-sounding Finding message by ``_scan_contents`` (not "a secret").
    """
    # DO_ENDPOINT_RE ([A-Za-z0-9][A-Za-z0-9-]*\.db\.ondigitalocean\.com)
    # backtracks O(n^2) on a long alnum/hyphen run (~minutes on a 200k-char
    # minified line). stdlib re has no possessive quantifiers, so gate it
    # behind an O(n) substring check: any real endpoint MUST contain this
    # literal, so the prefilter is a necessary condition — behavior is
    # identical, only the pathological scan is skipped. The other patterns'
    # forbidden-char classes are already linear, so they run as-is.
    do_hit = ".db.ondigitalocean.com" in line and bool(DO_ENDPOINT_RE.search(line))
    return (
        bool(CONN_URI_RE.search(line))
        or do_hit
        or bool(ODBC_SECRET_RE.search(line))
        or bool(MYSQL_URI_RE.search(line))
        or _has_snowflake_secret_pair(line)
    )


def _scan_file_lines(path: str, text: str) -> list[Finding]:
    """Findings for one file's content, one entry per offending line.

    Flattens the per-line scan out of ``_scan_contents`` so the outer loop
    over tracked files stays shallow. A secret-shaped line and a cluster-slug
    line are reported with distinct messages (the slug is real connection
    context, not a secret), preserving the original per-line precedence.
    """
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _scan_line_for_secret(line):
            findings.append(
                Finding(
                    rule_id="C2",
                    severity=Severity.ERROR,
                    message="possible committed connection string / secret",
                    locator=f"{path}:{lineno}",
                )
            )
        # A committed DO cluster slug is real connection context (not a secret,
        # but a real value the hard rule forbids). Reported separately so the
        # message does not overstate it as a "secret".
        elif DO_CLUSTER_SLUG_RE.search(line):
            findings.append(
                Finding(
                    rule_id="C2",
                    severity=Severity.ERROR,
                    message=(
                        "committed DigitalOcean cluster slug (real connection "
                        "context) -- move it to the gitignored .env"
                    ),
                    locator=f"{path}:{lineno}",
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
        findings.extend(_scan_file_lines(path, text))
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


def _index_gitattributes(path: Path) -> dict[str, tuple[int, set[str]]]:
    """Index a .gitattributes file: glob -> (1-based line number, remaining tokens).

    Blank and comment lines are skipped. A missing file yields an empty index.
    """
    declared: dict[str, tuple[int, set[str]]] = {}
    if not path.exists():
        return declared
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        glob = tokens[0]
        declared[glob] = (lineno, set(tokens[1:]))
    return declared


def _g4_required_findings(declared: dict[str, tuple[int, set[str]]]) -> list[Finding]:
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


@register("G4", ".gitattributes EOL policy")
def check_gitattributes_eol(ctx: RuleContext) -> Iterable[Finding]:
    """G4: each REQUIRED glob in .gitattributes must carry its eol/binary token.

    Subset (MUST-CONTAIN) check: extra benign entries are permitted. Matching is
    by exact first-token equality, never glob expansion, so the `* text=auto`
    catch-all does not satisfy any required glob.
    """
    declared = _index_gitattributes(ctx.repo_root / ".gitattributes")
    return _g4_required_findings(declared)
