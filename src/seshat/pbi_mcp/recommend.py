"""The Power BI execution-owner matrix as a pure decision function.

Input = a declared task INTENT (closed vocabulary) + the detected facts;
output = one categorical :class:`Recommendation` naming the governed surface,
why, the missing prerequisites, and the next HUMAN step. The original issue-450
cases and Phase 3's official report-authoring route map to distinct surface
tokens; missing readiness is always a named fail-closed result.

The only write in slice 2 is :func:`write_advisory` -- an explicit, opt-in
advisory record at ``.seshat/powerbi-mcp-recommendation.yaml`` that grants
nothing. It refuses to overwrite an existing record (write-once; delete the
old record deliberately to re-issue).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .detect import (
    ABSENT,
    CONFIG_ABSENT,
    CONFIG_FORBIDDEN_FLAG,
    CONFIG_UNPARSEABLE,
    CONFIG_WRITE_MODE,
    READINESS_PASS,
    DetectedFacts,
)
from .scan import refuse_if_secret_shaped

SCHEMA_VERSION = 2
ADVISORY_RELPATH = ".seshat/powerbi-mcp-recommendation.yaml"

# Closed intent vocabulary. The original section-7 cases remain stable; Phase 3
# adds report-authoring rather than overloading bounded report-formatting.
INTENT_MODEL_EDIT = "model-edit"
INTENT_PUBLISHED_QUERY = "published-query"
INTENT_REPORT_AUTHORING = "report-authoring"
INTENT_REPORT_FORMATTING = "report-formatting"
INTENT_DESKTOP_VERIFICATION = "desktop-verification"
INTENT_DB_CONNECTIVITY = "db-connectivity"
INTENT_CI_VALIDATION = "ci-validation"
INTENT_SENSITIVE_PRODUCTION = "sensitive-production"

INTENTS: tuple[str, ...] = (
    INTENT_MODEL_EDIT,
    INTENT_PUBLISHED_QUERY,
    INTENT_REPORT_AUTHORING,
    INTENT_REPORT_FORMATTING,
    INTENT_DESKTOP_VERIFICATION,
    INTENT_DB_CONNECTIVITY,
    INTENT_CI_VALIDATION,
    INTENT_SENSITIVE_PRODUCTION,
)

# Distinct surface tokens. Comments retain the original section-7 case numbers.
SURFACE_LOCAL_MODELING_MCP = "local-modeling-mcp"  # case 1
SURFACE_REMOTE_MCP = "remote-powerbi-mcp"  # case 2
SURFACE_OFFICIAL_REPORT_AUTHORING = "official-powerbi-report-authoring"
SURFACE_PBIR_ADAPTER = "pbir-authoring-adapter"  # case 3
SURFACE_DESKTOP_BRIDGE = "desktop-bridge"  # case 4
SURFACE_GATEWAY_SERVICE = "gateway-and-service"  # case 5
SURFACE_BLOCKED_ON_READINESS = "blocked-on-semantic-readiness"  # case 6
SURFACE_PBIP_FILE_VALIDATION = "pbip-file-validation"  # case 7
SURFACE_READ_ONLY_HARDENED = "read-only-hardened"  # case 8

GENERATED_NOTE = (
    "advisory only -- grants no approval, advances no readiness stage, and "
    "authorizes no MCP call or write; F016 stays parked pending an "
    "owner-ratified ADR"
)


@dataclass(frozen=True)
class Recommendation:
    """One categorical recommendation record -- no numeric score, ever."""

    intent: str
    surface: str
    why: str
    missing_prerequisites: tuple[str, ...]
    next_human_step: str
    blocked: bool


def _runtime_prerequisites(facts: DetectedFacts) -> list[str]:
    """Prerequisites for launching the LOCAL modeling MCP, from facts."""
    prereqs: list[str] = []
    if facts.node_runtime == ABSENT and facts.vendored_runtime == ABSENT:
        prereqs.append(
            "a local MCP runtime: install Node.js 20+ (npx "
            "@microsoft/powerbi-modeling-mcp) or vendor the platform binary "
            "under tools/powerbi-modeling-mcp/ (gitignored)"
        )
    if facts.mcp_config == CONFIG_ABSENT:
        prereqs.append(
            "copy .mcp.json.example to the gitignored .mcp.json (read-only default)"
        )
    elif facts.mcp_config == CONFIG_WRITE_MODE:
        prereqs.append(
            ".mcp.json requests write mode -- set --readonly (write is "
            "slice-5 territory, owner-ADR-gated)"
        )
    elif facts.mcp_config == CONFIG_UNPARSEABLE:
        prereqs.append(".mcp.json is unparseable -- fix or regenerate it")
    elif facts.mcp_config == CONFIG_FORBIDDEN_FLAG:
        prereqs.append(
            ".mcp.json carries --skipconfirmation -- forbidden in every "
            "mode; remove it before anything runs"
        )
    if facts.pbip_project == ABSENT:
        prereqs.append("a PBIP/TMDL project on disk (none detected)")
    return prereqs


def _recommend_model_edit(facts: DetectedFacts) -> Recommendation:
    # Section-7 case 6: readiness not passed blocks ALL Power BI mutations
    # and names the gate -- checked before any surface is even suggested.
    if facts.semantic_model_ready != READINESS_PASS:
        return Recommendation(
            intent=INTENT_MODEL_EDIT,
            surface=SURFACE_BLOCKED_ON_READINESS,
            why=(
                "the semantic_model_ready gate is "
                f"'{facts.semantic_model_ready}' -- no table records a pass, "
                "so every Power BI model mutation path is blocked fail-closed"
            ),
            missing_prerequisites=(
                "a committed semantic_model_ready = pass in "
                "mappings/<table>/readiness-status.yaml",
            ),
            next_human_step=(
                "advance the readiness spine (seshat next) until a named "
                "human records the semantic_model_ready pass; never route "
                "around the gate"
            ),
            blocked=True,
        )
    prereqs = _runtime_prerequisites(facts)
    blocked = facts.mcp_config == CONFIG_FORBIDDEN_FLAG
    return Recommendation(
        intent=INTENT_MODEL_EDIT,
        surface=SURFACE_LOCAL_MODELING_MCP,
        why=(
            "creating/modifying a PBIP/TMDL semantic model routes to the "
            "official local Power BI Modeling MCP -- read-only until the "
            "owner-ratified ADR lifts the F016 park; a mutation additionally "
            "needs a named-human publish_ready approval"
        ),
        missing_prerequisites=tuple(prereqs),
        next_human_step=(
            "satisfy the listed prerequisites, then run the read-only "
            "preflight (seshat pbi-mcp preflight); any write stays parked"
        ),
        blocked=blocked,
    )


def _recommend_published_query(facts: DetectedFacts) -> Recommendation:
    del facts  # tenant-side prerequisites are not locally detectable
    return Recommendation(
        intent=INTENT_PUBLISHED_QUERY,
        surface=SURFACE_REMOTE_MCP,
        why=(
            "querying an already-published semantic model routes to the "
            "official remote Power BI MCP server (query-only, post-publish; "
            "never a readiness-gate input)"
        ),
        missing_prerequisites=(
            "tenant setting enabled: 'Users can use the Power BI Model "
            "Context Protocol server endpoint (preview)'",
            "Build permission on the target semantic model",
            "a Copilot license for the Generate Query tool",
            "Entra ID sign-in (machine-local; never committed)",
        ),
        next_human_step=(
            "verify each prerequisite with the Power BI tenant admin; if any "
            "is unmet, stop -- do not work around it"
        ),
        blocked=False,
    )


def _recommend_report_authoring(facts: DetectedFacts) -> Recommendation:
    prereqs: list[str] = []
    if facts.target is None:
        prereqs.append(
            "an exact governed table selected with --target <table>; another "
            "table's readiness can never authorize this report"
        )
    elif facts.dashboard_ready != READINESS_PASS:
        prereqs.append(
            f"dashboard_ready = pass for mappings/{facts.target}/readiness-status.yaml"
        )
    prereqs.append(
        "the official Microsoft powerbi-report-authoring skill proven activated "
        "and discoverable by this harness (Phase 6); installed alone is not enough"
    )
    gate = (
        f"target '{facts.target}' records dashboard_ready = pass"
        if facts.target is not None and facts.dashboard_ready == READINESS_PASS
        else (
            "no exact target was declared"
            if facts.target is None
            else f"target '{facts.target}' dashboard_ready is '{facts.dashboard_ready}'"
        )
    )
    return Recommendation(
        intent=INTENT_REPORT_AUTHORING,
        surface=SURFACE_OFFICIAL_REPORT_AUTHORING,
        why=(
            f"{gate}; native PBIR page, visual, filter, slicer, binding, and "
            "theme authoring belongs to Microsoft's official report-authoring "
            "skill, while Seshat owns the design gate and validation"
        ),
        missing_prerequisites=tuple(prereqs),
        next_human_step=(
            "verify official-skill discovery through the supported harness, then "
            "delegate native PBIR authoring and return the result to Seshat's "
            "binding, blueprint, and static validators; do not emulate the skill"
        ),
        # Phase 6 owns activation/discovery proof. Until that proof is represented,
        # this route is intentionally selected but not executable.
        blocked=True,
    )


def _recommend_report_formatting(facts: DetectedFacts) -> Recommendation:
    del facts
    return Recommendation(
        intent=INTENT_REPORT_FORMATTING,
        surface=SURFACE_PBIR_ADAPTER,
        why=(
            "theme, page layout, geometry, and visual formatting stay on the "
            "existing PBIR-authoring adapter (F034) -- deterministic, "
            "local-file, no MCP runtime needed"
        ),
        missing_prerequisites=(),
        next_human_step=(
            "use the shipped PBIR verbs (theme-gen, pbir-apply-theme, "
            "pbir-format-visual, pbir-set-geometry, ...) via the "
            "powerbi-workflows skill"
        ),
        blocked=False,
    )


def _recommend_desktop_verification(facts: DetectedFacts) -> Recommendation:
    del facts
    return Recommendation(
        intent=INTENT_DESKTOP_VERIFICATION,
        surface=SURFACE_DESKTOP_BRIDGE,
        why=(
            "live Desktop verification and screenshots belong to the Power "
            "BI Desktop Bridge -- a separate optional integration, not MCP"
        ),
        missing_prerequisites=("Power BI Desktop installed (never in CI)",),
        next_human_step=(
            "see docs/powerbi-connection.md for the Desktop Bridge flow; "
            "keep it out of CI"
        ),
        blocked=False,
    )


def _recommend_db_connectivity(facts: DetectedFacts) -> Recommendation:
    del facts
    return Recommendation(
        intent=INTENT_DB_CONNECTIVITY,
        surface=SURFACE_GATEWAY_SERVICE,
        why=(
            "database connectivity and scheduled refresh belong to the "
            "Power BI Gateway + Service -- neither MCP server touches them"
        ),
        missing_prerequisites=(
            "a tenant-managed gateway installation and data-source "
            "credentials (configured outside this repo)",
        ),
        next_human_step=(
            "route the request to the tenant's gateway administrator; "
            "nothing in this repo stores those credentials"
        ),
        blocked=False,
    )


def _recommend_ci_validation(facts: DetectedFacts) -> Recommendation:
    del facts
    return Recommendation(
        intent=INTENT_CI_VALIDATION,
        surface=SURFACE_PBIP_FILE_VALIDATION,
        why=(
            "CI / Linux / non-Desktop environments get deterministic "
            "PBIP/TMDL file validation only -- Power BI Desktop is never "
            "required, and an unavailable remote server is a graceful skip, "
            "not a failure"
        ),
        missing_prerequisites=(),
        next_human_step=(
            "run the shipped offline validators (seshat check, "
            "pbir-validate-bindings, pbir-validate-blueprint) in CI"
        ),
        blocked=False,
    )


def _recommend_sensitive_production(facts: DetectedFacts) -> Recommendation:
    del facts
    return Recommendation(
        intent=INTENT_SENSITIVE_PRODUCTION,
        surface=SURFACE_READ_ONLY_HARDENED,
        why=(
            "a sensitive / production environment gets the hardened posture: "
            "read-only everywhere, stricter named-human approval, and NO "
            "Service-Principal query path where row-level security matters "
            "(the remote server does not enforce RLS for Service Principal "
            "callers)"
        ),
        missing_prerequisites=(
            "a named-human review of the approval posture for this environment",
        ),
        next_human_step=(
            "have the owner confirm the read-only + stricter-approval "
            "posture before any Power BI surface is used here"
        ),
        blocked=False,
    )


_HANDLERS = {
    INTENT_MODEL_EDIT: _recommend_model_edit,
    INTENT_PUBLISHED_QUERY: _recommend_published_query,
    INTENT_REPORT_AUTHORING: _recommend_report_authoring,
    INTENT_REPORT_FORMATTING: _recommend_report_formatting,
    INTENT_DESKTOP_VERIFICATION: _recommend_desktop_verification,
    INTENT_DB_CONNECTIVITY: _recommend_db_connectivity,
    INTENT_CI_VALIDATION: _recommend_ci_validation,
    INTENT_SENSITIVE_PRODUCTION: _recommend_sensitive_production,
}


def recommend(intent: str, facts: DetectedFacts) -> Recommendation:
    """Map one declared intent + detected facts to one recommendation (pure)."""
    handler = _HANDLERS.get(intent)
    if handler is None:
        raise ValueError(
            f"unknown intent {intent!r}; expected one of: {', '.join(INTENTS)}"
        )
    return handler(facts)


class AdvisoryWriteError(ValueError):
    """The advisory record could not be written safely (e.g. it exists)."""


def _yaml_str(value: str) -> str:
    """Quote a scalar for the hand-rendered YAML (values are ASCII by
    construction; quoting keeps ':' and '--' unambiguous)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_list(items: tuple[str, ...], indent: str) -> list[str]:
    return [f"{indent}- {_yaml_str(item)}" for item in items]


def render_advisory(
    facts: DetectedFacts, rec: Recommendation, generated_at: str
) -> str:
    """Hand-rendered, deterministic, ASCII-only YAML advisory record."""
    lines: list[str] = [
        "# GENERATED advisory record -- seshat pbi-mcp doctor --write-advisory",
        "# Read-only: this file grants nothing (see generated_note).",
        f"schema_version: {SCHEMA_VERSION}",
        f"generated_at: {_yaml_str(generated_at)}",
        f"generated_note: {_yaml_str(GENERATED_NOTE)}",
        "detected:",
        f"  node_runtime: {_yaml_str(facts.node_runtime)}",
        f"  vendored_runtime: {_yaml_str(facts.vendored_runtime)}",
        f"  mcp_config: {_yaml_str(facts.mcp_config)}",
        f"  pbip_project: {_yaml_str(facts.pbip_project)}",
        f"  target: {_yaml_str(facts.target or 'none')}",
        f"  semantic_model_ready: {_yaml_str(facts.semantic_model_ready)}",
    ]
    if facts.semantic_ready_tables:
        lines.append("  semantic_ready_tables:")
        lines.extend(_yaml_list(facts.semantic_ready_tables, "    "))
    else:
        lines.append("  semantic_ready_tables: []")
    lines.append(f"  dashboard_ready: {_yaml_str(facts.dashboard_ready)}")
    if facts.dashboard_ready_tables:
        lines.append("  dashboard_ready_tables:")
        lines.extend(_yaml_list(facts.dashboard_ready_tables, "    "))
    else:
        lines.append("  dashboard_ready_tables: []")
    lines.extend(
        [
            f"  publish_ready_approval: {_yaml_str(facts.publish_ready_approval)}",
            "recommendation:",
            f"  intent: {_yaml_str(rec.intent)}",
            f"  surface: {_yaml_str(rec.surface)}",
            f"  why: {_yaml_str(rec.why)}",
            f"  blocked: {'true' if rec.blocked else 'false'}",
        ]
    )
    if rec.missing_prerequisites:
        lines.append("  missing_prerequisites:")
        lines.extend(_yaml_list(rec.missing_prerequisites, "    "))
    else:
        lines.append("  missing_prerequisites: []")
    lines.append(f"  next_human_step: {_yaml_str(rec.next_human_step)}")
    text = "\n".join(lines) + "\n"
    if not text.isascii():
        raise AdvisoryWriteError("advisory rendering produced non-ASCII output")
    return text


def write_advisory(
    repo_root: Path,
    facts: DetectedFacts,
    rec: Recommendation,
    *,
    generated_at: str | None = None,
) -> Path:
    """Write the advisory record once; refuse if one already exists.

    The ONLY write in slice 2, and only ever called under the explicit
    ``--write-advisory`` flag -- never as a side effect of the doctor.
    """
    target = Path(repo_root) / ADVISORY_RELPATH
    if target.exists():
        raise AdvisoryWriteError(
            f"refused: {ADVISORY_RELPATH} already exists -- the advisory is "
            "write-once; delete it deliberately to re-issue"
        )
    stamp = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = render_advisory(facts, rec, stamp)
    refuse_if_secret_shaped(text, context=ADVISORY_RELPATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target
