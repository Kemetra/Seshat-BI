"""User workspace initializer (spec 107, roadmap M3) -- SCAFFOLDING ONLY.

``init_project`` creates a FRESH, empty Retail-BI *project workspace* for a new
user: ``seshat init-project my-retail-bi`` gives them a ready-but-empty tree,
distinct from ``retail init`` (which bootstraps ``.seshat/`` + fenced regions
INTO an existing repo -- see ``kit_init.bootstrap``). This module never touches
that flow: it does not modify or duplicate ``retail init``'s behavior (FR-002).

Deviation from plan.md (recorded for owner review -- the spec is HELD/DRAFT):
the generated workspace does NOT call ``kit_init.bootstrap()`` / write
``.seshat/compass.yaml``. A pre-implementation spike proved that doing so flips
``seshat.kit_lint.is_bootstrapped()`` to True, which activates the KIT_SELF
rule tier (A1, A3, AP1, SC1, SC2, SF1, DF1, AQ1, DR1). Those rules require the
KIT's OWN internal manifests (docs/routing/routes.yaml,
docs/quality/status-claims.yaml, a KPI domain corpus, ...) that a fresh user
workspace never has and must never fabricate (FR-004). FR-006 ("the generated
workspace passes `retail check`") is the harder, must-verify constraint, so the
workspace ships as a genuinely non-bootstrapped ("drop-in tier") repo: no
``.seshat/`` substrate is written at all. The KIT_SELF rules then correctly
SKIP (INFO), matching how any repo the kit was merely downloaded into behaves.
See specs/107-user-workspace-init/tasks.md for the full spike record.

Pure stdlib ``pathlib`` only -- no DB, no network, no third-party import
(FR-005 / B1 / B3). Deterministic and idempotent: a re-run over an unchanged
target writes byte-identical content and never duplicates a line (FR-001).
Refuses a non-empty target without ``force=True`` (FR-003) and refuses a target
that resolves outside the current working directory unless it is a plain
relative name under it (path-traversal guard). Writes NO source data, NO
credentials, NO fabricated metric/readiness content (FR-004): ``.env.example``
carries parameter NAMES only, never real values.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# The generated workspace shape (plan.md), minus the `.seshat/` bootstrap --
# see the module docstring for why that piece is deliberately omitted.
# ---------------------------------------------------------------------------

# The medallion SQL home is `warehouse/migrations/` -- the ONE location every
# governance rule (sql, date_spine, reload_idempotency, rls_access), the impact
# map, and the Dagster silver/gold build actually read, and the layout the
# reference example ships (#349). The former `warehouse/{bronze,silver,gold}/`
# dirs were read by NOTHING: SQL scaffolded there was invisible to `retail check`
# (silent false-pass) and dead-ended the Dagster build.
_EMPTY_DIRS: tuple[str, ...] = (
    "mappings",
    "warehouse/migrations",
    "powerbi",
    "reports",
    "evidence",
)

# git does not track empty directories; a `.gitkeep` marker makes each empty
# dir survive a real `git add -A` + commit so the shape is real once the user
# commits it (FR-001 shape must be genuine, not just present in the working
# tree before version control).
_GITKEEP_NAME = ".gitkeep"

_GITIGNORE_TEXT = (
    "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n.env\n.env.*\n!.env.example\n"
)

_GITATTRIBUTES_TEXT = (
    "* text=auto\n"
    "\n"
    "*.tmdl   text eol=crlf\n"
    "*.pbir   text eol=crlf\n"
    "*.pbism  text eol=crlf\n"
    "*.json   text eol=crlf\n"
    "*.sql    text eol=lf\n"
    "*.md     text eol=lf\n"
    "*.py     text eol=lf\n"
    "\n"
    "*.pbix   binary\n"
    "*.abf    binary\n"
    "*.png    binary\n"
)

# Parameter NAMES only -- every value stays empty (FR-004). Matches the shape
# of the kit's own .env.example (docs/powerbi-connection.md: Power BI reads its
# credentials from the gateway, never this file).
_ENV_EXAMPLE_TEXT = (
    "# Analytics database connection parameters.\n"
    "# Copy this file to .env and fill in real values. .env is git-ignored;\n"
    "# never commit secrets. See README.md for the readiness flow.\n"
    "\n"
    "ANALYTICS_DB_HOST=\n"
    "ANALYTICS_DB_PORT=25060\n"
    "ANALYTICS_DB_NAME=\n"
    "ANALYTICS_DB_USER=\n"
    "ANALYTICS_DB_PASSWORD=\n"
    "ANALYTICS_DB_SSLMODE=require\n"
)

_README_TEXT = (
    "# Retail-BI workspace\n"
    "\n"
    "A fresh Retail-BI project workspace, scaffolded by "
    "`seshat init-project` (spec 107).\n"
    "\n"
    "## Layout\n"
    "\n"
    "- `mappings/` -- source-to-mapping evidence (the source-mapping gate "
    "populates this)\n"
    "- `warehouse/migrations/` -- the medallion SQL home (numbered silver/gold "
    "migration files; this is where `retail check` and the build read)\n"
    "- `powerbi/` -- the PBIP project home\n"
    "- `reports/` -- dashboard-spec / blueprint homes\n"
    "- `evidence/` -- evidence-pack output home\n"
    "\n"
    "## Next steps\n"
    "\n"
    "1. Copy `.env.example` to `.env` and fill in your database connection "
    "parameters (never commit `.env`).\n"
    "2. Initialize git and make a first commit -- the checker reads git-tracked "
    "state, so it must run inside a git repo with at least one commit:\n"
    '   `git init && git add -A && git commit -m "chore: scaffold workspace"`\n'
    "3. Run `retail check` to confirm the workspace baseline is clean.\n"
    "4. Follow the readiness flow: profile your first table, then map it "
    "(the source-mapping gate) before building silver/gold SQL in "
    "`warehouse/migrations/`.\n"
)

_WAREHOUSE_README_TEXT = (
    "# warehouse/\n"
    "\n"
    "`migrations/` -- the medallion SQL home: numbered, idempotent silver/gold "
    "migration files (e.g. `0003_create_silver_<table>.sql`, "
    "`0004_create_gold_<table>_star.sql`). Every governance rule and the "
    "orchestrated build read SQL from here. Power BI reads the `gold` schema "
    "only.\n"
)

_POWERBI_README_TEXT = (
    "# powerbi/\n"
    "\n"
    "The PBIP project home. Empty until a Power BI Desktop project is saved "
    "here as Power BI Project (.pbip).\n"
)


def _validate_target(name: str) -> Path:
    """Resolve ``name`` to an absolute path, refusing anything outside the CWD.

    A bare relative name (``my-retail-bi``) or a relative/absolute path that
    resolves under the current working directory is allowed. Anything that
    resolves OUTSIDE the CWD (``../elsewhere``, an absolute path elsewhere) is
    refused with ``ValueError`` -- the path-traversal / outside-CWD guard.
    """
    cwd = Path.cwd().resolve()
    candidate = (cwd / name).resolve()
    try:
        candidate.relative_to(cwd)
    except ValueError:
        raise ValueError(
            f"refusing to scaffold outside the current working directory: "
            f"{name!r} resolves to {candidate}, which is not under {cwd}"
        ) from None
    return candidate


def _write_text(path: Path, text: str) -> Path:
    """Write UTF-8 without BOM, ``\\n`` line endings (Windows-stable, Principle IX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _guard_target(target: Path, force: bool) -> None:
    """Refuse a non-directory target, or a non-empty one without ``force``
    (FR-003) -- raises ``FileExistsError`` and the caller writes NOTHING."""
    if not target.exists():
        return
    if not target.is_dir():
        raise FileExistsError(f"target exists and is not a directory: {target}")
    if any(target.iterdir()) and not force:
        raise FileExistsError(
            f"target directory is not empty: {target} "
            f"(pass force=True / --force to scaffold into it anyway)"
        )


def _scaffold_empty_dirs(target: Path) -> list[Path]:
    """Create each empty workspace dir + its ``.gitkeep``; idempotent.

    The ``.gitkeep`` write goes through the shared hardened writer (#352): the
    former ``if not keep.exists(): _write_text`` followed a pre-planted symlink
    out of the workspace. ``safe_write.write_if_absent`` refuses that (and any
    non-file collision) and keeps the write non-destructive + atomic.
    """
    from seshat.safe_write import write_if_absent

    written: list[Path] = []
    for rel in _EMPTY_DIRS:
        d = target / rel
        d.mkdir(parents=True, exist_ok=True)
        written.append(d)
        write_if_absent(target, f"{rel}/{_GITKEEP_NAME}", b"")
        written.append(d / _GITKEEP_NAME)
    return written


def _scaffold_files(target: Path) -> list[Path]:
    """Write the workspace's static template files; deterministic, byte-identical."""
    files = (
        ("README.md", _README_TEXT),
        ("warehouse/README.md", _WAREHOUSE_README_TEXT),
        ("powerbi/README.md", _POWERBI_README_TEXT),
        (".env.example", _ENV_EXAMPLE_TEXT),
        (".gitignore", _GITIGNORE_TEXT),
        (".gitattributes", _GITATTRIBUTES_TEXT),
    )
    return [_write_text(target / rel, text) for rel, text in files]


def init_project(name: str, force: bool = False) -> list[Path]:
    """Scaffold a fresh Retail-BI project workspace at ``name``.

    ``name`` is resolved relative to the current working directory (FR-001);
    resolving outside the CWD raises ``ValueError`` (path-traversal guard).
    Refuses a target that already exists and is non-empty unless
    ``force=True`` (FR-003) -- refusal raises ``FileExistsError`` and writes
    NOTHING. Deterministic and idempotent: re-running (with ``force=True`` if
    the target now exists) writes byte-identical content and never duplicates
    a line.

    Returns the list of paths written or ensured on this call, as ``Path``
    objects, most useful for a caller that wants to report what happened.
    """
    target = _validate_target(name)
    _guard_target(target, force)
    target.mkdir(parents=True, exist_ok=True)
    return _scaffold_empty_dirs(target) + _scaffold_files(target)
