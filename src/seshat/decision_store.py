"""Decision Store loader (spec 121).

Fail-closed reader for the project Decision Store: the three per-concern YAML
files that record business decisions from the Business Knowledge Interview.

    .seshat/semantic-decisions.yaml   grain / PK / relationships / PII / exclusions
    .seshat/kpi-contracts.yaml        KPI meaning + policy rulings
    .seshat/cleaning-rules.yaml       missing-value + cleaning rulings

This is a static text/YAML read. It never opens a database, never runs Power BI,
never grants an approval, and never advances a readiness stage. Every consumer
(the DS1-DS5 rules, the gate, the review generator) reads through this loader so
the fail-closed contract lives in one place: a malformed store, an unknown status,
or an unreadable file yields a structured problem, never a raised exception and
never a silent skip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The three canonical store files, relative to the project workspace root. The
# DS rules, the gate, and the review generator all key on these exact paths so a
# blank template under templates/ can never be mistaken for a live store.
STORE_PATHS: tuple[str, ...] = (
    ".seshat/semantic-decisions.yaml",
    ".seshat/kpi-contracts.yaml",
    ".seshat/cleaning-rules.yaml",
)

# The nine-status decision lifecycle (FR-014).
STATUS_VALUES: frozenset[str] = frozenset(
    {
        "proposed",
        "approved",
        "rejected",
        "pending",
        "needs_user_input",
        "needs_sample",
        "blocked",
        "deferred",
        "superseded",
    }
)

# The eleven critical decision types (FR-018). Non-critical types are permitted and
# are the only ones eligible for batches (DS3).
CRITICAL_DECISION_TYPES: frozenset[str] = frozenset(
    {
        "kpi_definition",
        "pii_handling",
        "table_grain",
        "primary_key",
        "relationship_cardinality",
        "missing_value_rule",
        "data_exclusion",
        "policy_ruling",
        "dashboard_blueprint_approval",
        "report_intent_approval",
        "publish_export",
    }
)

# Agent proposal confidence (FR-015). Never approval, never a readiness signal.
CONFIDENCE_VALUES: frozenset[str] = frozenset({"low", "medium", "high"})

# Statuses that leave a decision UNRESOLVED for gate purposes. `rejected` and
# `superseded` are TERMINAL, not open (data-model): a rejected assumption and a
# superseded record are both settled -- they do not themselves block, and a stage
# that still needs the decision blocks on the ABSENCE of an approval (the gate's
# evidence-presence rule), not on the terminal record.
_OPEN_STATUSES: frozenset[str] = frozenset(
    {
        "proposed",
        "pending",
        "needs_user_input",
        "needs_sample",
        "blocked",
        "deferred",
    }
)

# Terminal non-open statuses: settled records that do not block by themselves.
_TERMINAL_STATUSES: frozenset[str] = frozenset({"approved", "rejected", "superseded"})


@dataclass(frozen=True)
class StoreProblem:
    """A fail-closed problem found while loading. Carries enough to become a
    ``Finding`` (rule_id supplied by the caller) or a gate blocking reason."""

    path: str
    locator: str
    message: str


@dataclass(frozen=True)
class LoadedStore:
    """The parsed content of one store file plus any load problems.

    ``decisions`` and ``batches`` are the raw list payloads (each item still a
    plain dict); shape validation beyond "is a mapping with the right top-level
    keys" is the DS rules' job. ``problems`` is non-empty only for fail-closed
    conditions (unreadable, invalid YAML, wrong top-level shape)."""

    path: str
    decisions: tuple[dict[str, Any], ...] = ()
    batches: tuple[dict[str, Any], ...] = ()
    problems: tuple[StoreProblem, ...] = ()
    present: bool = False

    @property
    def ok(self) -> bool:
        return self.present and not self.problems


def store_files(tracked_files: tuple[str, ...]) -> list[str]:
    """The store files actually present among the tracked files, sorted.

    Absent store => empty list => callers do nothing (pass-silent). Blank
    ``templates/`` files never match because the selector is exact-membership on
    the canonical ``.seshat/`` paths."""
    present = frozenset(STORE_PATHS)
    return sorted(p for p in tracked_files if p in present)


def load_store_file(repo_root: Path | str, rel: str) -> LoadedStore:
    """Read and shallow-parse one store file. Never raises; a failure becomes a
    ``StoreProblem`` so the caller can fail closed."""
    root = Path(repo_root)
    try:
        raw = (root / rel).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return LoadedStore(
            path=rel,
            present=True,
            problems=(StoreProblem(rel, rel, f"could not read decision store: {exc}"),),
        )

    import yaml  # lazy: keep retail check import path stdlib-light

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return LoadedStore(
            path=rel,
            present=True,
            problems=(
                StoreProblem(rel, rel, f"decision store is not valid YAML: {exc}"),
            ),
        )

    if data is None:
        # An empty file is a legitimate empty store (no decisions yet).
        return LoadedStore(path=rel, present=True)

    if not isinstance(data, dict):
        return LoadedStore(
            path=rel,
            present=True,
            problems=(StoreProblem(rel, rel, "decision store must be a mapping"),),
        )

    problems: list[StoreProblem] = []
    allowed_keys = {"decisions", "batches"}
    unknown = sorted(set(data) - allowed_keys)
    if unknown:
        problems.append(
            StoreProblem(
                rel,
                rel,
                f"decision store has unknown top-level key(s) {unknown}; "
                "allowed keys are 'decisions' and 'batches'",
            )
        )

    decisions = _coerce_dict_list(data.get("decisions"), rel, "decisions", problems)
    batches = _coerce_dict_list(data.get("batches"), rel, "batches", problems)

    return LoadedStore(
        path=rel,
        decisions=tuple(decisions),
        batches=tuple(batches),
        problems=tuple(problems),
        present=True,
    )


def load_store(repo_root: Path | str, tracked_files: tuple[str, ...]) -> "Store":
    """Load every present store file into one aggregate view."""
    files = tuple(load_store_file(repo_root, rel) for rel in store_files(tracked_files))
    return Store(files=files)


AUTHORITY_CONTRACT_REL = "contracts/knowledge/approval-authority.yaml"


def load_authority_map(
    repo_root: Path | str,
) -> dict[str, frozenset[str]] | None:
    """Read the decision_type -> eligible authority classes map from the contract.

    Returns None (fail-closed: eligibility cannot be validated) if the contract is
    missing or malformed. Shared by DS2 and the gate."""
    path = Path(repo_root) / AUTHORITY_CONTRACT_REL
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    import yaml

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("eligibility"), dict):
        return None
    return {
        dtype: frozenset(_norm_token(c) for c in classes if isinstance(c, str))
        for dtype, classes in data["eligibility"].items()
        if isinstance(dtype, str) and isinstance(classes, list)
    }


def _coerce_dict_list(
    value: object, rel: str, key: str, problems: list[StoreProblem]
) -> list[dict[str, Any]]:
    """Return ``value`` as a list of dict records, recording a problem for any
    non-list value or non-dict member (fail-closed, never raises)."""
    if value is None:
        return []
    if not isinstance(value, list):
        problems.append(StoreProblem(rel, f"{rel}:{key}", f"'{key}' must be a list"))
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            records.append(item)
        else:
            problems.append(
                StoreProblem(
                    rel,
                    f"{rel}:{key}[{index}]",
                    f"'{key}' entry {index} must be a mapping",
                )
            )
    return records


@dataclass(frozen=True)
class Store:
    """Aggregate over the present store files."""

    files: tuple[LoadedStore, ...] = ()

    @property
    def present(self) -> bool:
        return any(f.present for f in self.files)

    @property
    def problems(self) -> tuple[StoreProblem, ...]:
        return tuple(p for f in self.files for p in f.problems)

    def decisions(self) -> list[dict[str, Any]]:
        return [d for f in self.files for d in f.decisions]

    def batches(self) -> list[dict[str, Any]]:
        return [b for f in self.files for b in f.batches]


def is_critical(decision_type: object) -> bool:
    return isinstance(decision_type, str) and decision_type in CRITICAL_DECISION_TYPES


def is_open_status(status: object) -> bool:
    """True for a status that leaves a decision unresolved for gating."""
    return isinstance(status, str) and status in _OPEN_STATUSES


def is_known_status(status: object) -> bool:
    """True for any recognized status word (open or terminal). An unrecognized
    status is malformed and must fail closed at every consumer."""
    return isinstance(status, str) and status in STATUS_VALUES


# --- shared predicates: ONE source of truth for both the DS rules and the gate ---
# (so the static lint and the verdict can never diverge on what "valid" means).


def scope_keys(scope: object) -> list[str]:
    """Flat scope keys (``kind:value``) for a decision's scope; [] for a
    malformed scope. Non-string leaves are skipped."""
    if not isinstance(scope, dict):
        return []
    keys: list[str] = []
    for kind in ("tables", "columns", "kpis", "artifacts"):
        value = scope.get(kind)
        if isinstance(value, list):
            keys += [f"{kind}:{v}" for v in value if isinstance(v, str)]
    return keys


def active_scope_conflicts(
    decisions: list[dict[str, Any]],
) -> list[tuple[str, str, list[str]]]:
    """Return (decision_type, scope_key, ids) for every set of 2+ ACTIVE
    (non-terminal) records of the same type on the same scope key -- an
    unresolved conflict. Shared by DS4 and the gate so they never disagree."""
    active: dict[tuple[str, str], list[str]] = {}
    for rec in decisions:
        if rec.get("status") in ("superseded", "rejected"):
            continue
        dtype, did = rec.get("decision_type"), rec.get("id")
        if not isinstance(dtype, str) or not isinstance(did, str):
            continue
        for key in scope_keys(rec.get("scope")):
            active.setdefault((dtype, key), []).append(did)
    return [
        (dtype, key, sorted(ids))
        for (dtype, key), ids in active.items()
        if len(ids) > 1
    ]


# Owner shape: "Person Name (authority_class)". Validates the SHAPE only; the class
# VOCABULARY lives in contracts/knowledge/approval-authority.yaml, checked by the
# eligibility step -- so report_owner is valid for its decision type without editing
# the readiness-spine class set.
_OWNER_SHAPE_RE = re.compile(r"^(?P<name>[^()]+?)\s*\(\s*(?P<role>[^()]+?)\s*\)$")
_ROLE_TOKENS: frozenset[str] = frozenset(
    {"analyst", "governance", "data_owner", "metric_owner", "report_owner", "owner"}
)

# The metadata fields an approved critical decision MUST carry (FR-020).
APPROVAL_REQUIRED_FIELDS: tuple[str, ...] = (
    "approved_by",
    "approved_at",
    "source",
    "evidence",
    "evidence_identity",
    "reviewed_scope",
)


def _norm_token(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().lower())


def owner_shape_ok(owner: object) -> bool:
    """True for a well-formed "Person Name (class_token)"; class membership is not
    checked here (eligibility does that)."""
    if not isinstance(owner, str):
        return False
    match = _OWNER_SHAPE_RE.match(owner.strip())
    if match is None:
        return False
    name = match.group("name").strip()
    if not name or _norm_token(name) in _ROLE_TOKENS:
        return False
    return bool(match.group("role").strip())


def owner_class(owner: object) -> str | None:
    """The normalized authority class from a shape-valid owner string, else None."""
    if not isinstance(owner, str):
        return None
    match = _OWNER_SHAPE_RE.match(owner.strip())
    return _norm_token(match.group("role")) if match else None


def _eligibility_valid(
    decision: dict[str, Any],
    owner: object,
    authority: dict[str, frozenset[str]] | None,
) -> tuple[bool, str | None]:
    """Authority-class eligibility for a critical decision. Non-critical => valid."""
    did = decision.get("id", "<no-id>")
    dtype = decision.get("decision_type")
    if not is_critical(dtype):
        return True, None
    if authority is None:
        return False, f"{did}: cannot validate eligibility (authority contract absent)"
    eligible = authority.get(dtype)
    if not eligible:
        return False, f"{did}: no eligibility declared for {dtype!r}"
    if owner_class(owner) not in eligible:
        return False, f"{did}: class {owner_class(owner)!r} ineligible for {dtype!r}"
    return True, None


def approval_is_valid(
    decision: dict[str, Any], authority: dict[str, frozenset[str]] | None
) -> tuple[bool, str | None]:
    """The ONE approval-validity predicate shared by DS2 and the gate.

    Valid only when every required field is present, approved_by has the
    named-human-plus-class shape, and (for a critical decision) the class is
    eligible per the authority contract. ``authority is None`` => eligibility
    cannot be validated => invalid (fail closed)."""
    approval = decision.get("approval")
    did = decision.get("id", "<no-id>")
    if not isinstance(approval, dict):
        return False, f"{did}: no approval block"
    missing = [k for k in APPROVAL_REQUIRED_FIELDS if not approval.get(k)]
    if missing:
        return False, f"{did}: approval missing {missing}"
    owner = approval.get("approved_by")
    if not owner_shape_ok(owner):
        return False, f"{did}: invalid approved_by {owner!r}"
    return _eligibility_valid(decision, owner, authority)
