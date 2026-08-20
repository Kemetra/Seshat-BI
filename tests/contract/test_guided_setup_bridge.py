"""The guided-setup bridge's boundary invariants (spec 155, contracts/).

These are the assertions that stop the feature drifting into the surfaces it is
supposed to compose. Several are source-level on purpose: "this module contains
no installer call site" is a property of the code, and a behavioural test would
pass right up until someone added one behind a branch it did not exercise.
"""

from __future__ import annotations

from pathlib import Path


def _source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def _code_only(module) -> str:
    """The module's source with docstrings and comments removed.

    Every "this module contains no X call site" assertion below runs against
    this rather than the raw text. A module that documents its own boundaries --
    as these deliberately do -- otherwise fails its own assertion because the
    forbidden token appears in the sentence saying it must not appear, and the
    obvious "fix" is to delete the documentation. Stripping prose keeps the
    assertion about code, which is what it was always meant to be about.
    """
    source = _source(module)
    skip = _docstring_lines(source)
    cuts = _comment_cuts(source)
    # Rebuilt LINE BY LINE, keeping the original layout. Joining tokens instead
    # would break every multi-token phrase apart -- "subprocess.run" becomes
    # three tokens -- so each forbidden-token assertion would pass whether or not
    # the call site was there. `test_the_prose_stripper_leaves_the_code_intact`
    # exists because that is exactly what the first version of this helper did.
    return "\n".join(
        line[: cuts[number]] if number in cuts else line
        for number, line in enumerate(source.splitlines(), start=1)
        if number not in skip
    )


def _docstring_lines(source: str) -> set[int]:
    """Line numbers occupied by a module, class, or function docstring."""
    import ast

    lines: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        value = _first_constant(node)
        if value is not None:
            lines.update(range(value.lineno, (value.end_lineno or 0) + 1))
    return lines


def _first_constant(node):
    """The node's leading string constant, when it has one."""
    import ast

    body = getattr(node, "body", [])
    if not body or not isinstance(body[0], ast.Expr):
        return None
    value = body[0].value
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value
    return None


def _comment_cuts(source: str) -> dict[int, int]:
    """Per line, the column where its first comment starts."""
    import io
    import tokenize

    cuts: dict[int, int] = {}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        line, column = token.start
        cuts[line] = min(column, cuts.get(line, column))
    return cuts


def _catalog_tokens() -> set[str]:
    """Component ids and coordinates, read from the catalog at test time."""
    from seshat.integrations.catalog import DEFAULT_PROFILE, PROFILES

    tokens: set[str] = set()
    for item in PROFILES[DEFAULT_PROFILE]:
        tokens.add(item.id)
        tokens.add(item.coordinate)
    return {token for token in tokens if token}


def test_the_prose_stripper_leaves_the_code_intact() -> None:
    """Guard the guard: a stripper that gutted the source would pass everything.

    Every source-level assertion below would go vacuously green if `_code_only`
    returned nothing useful, so its output is checked to still carry the module's
    real declarations.
    """
    from seshat.integrations import guided_setup

    code = _code_only(guided_setup)

    assert "def derive_scope" in code
    assert "def readiness_from" in code
    assert "DerivedScope" in code
    assert "Eligibility is spec" not in code  # the docstring really is gone


# --------------------------------------------------------------------------- #
# Invariant 1: spec 153's proof still holds.
# --------------------------------------------------------------------------- #


def test_derivation_still_holds_no_execution_or_approval_call_site() -> None:
    """Invariant 1: this feature must not have moved execution into derivation.

    Spec 153's FR-017/FR-018 boundaries are proved by exactly this shape of
    assertion. Re-asserted here so that if spec 155 ever edits that file, the
    failure names spec 155 as the cause instead of looking like a spec-153
    regression.
    """
    from seshat.integrations import derivation

    source = _code_only(derivation)
    for forbidden in (
        "apply_profile(",
        "live_resolvers(",
        "write_lock(",
        "install(",
        "approved",
        "authorize",
        "--yes",
    ):
        assert forbidden not in source, forbidden


# --------------------------------------------------------------------------- #
# Invariants 2, 3, 7: the bridge owns no truth and executes nothing.
# --------------------------------------------------------------------------- #


def test_the_bridge_declares_no_component_or_coordinate_of_its_own() -> None:
    """Invariant 2 (FR-002): no second source of provider truth."""
    from seshat.integrations import guided_setup

    source = _source(guided_setup)
    leaked = sorted(token for token in _catalog_tokens() if token in source)

    assert leaked == [], leaked


def test_the_bridge_reads_no_caller_supplied_environment_or_argv() -> None:
    """Invariant 3 (FR-007): the scope cannot be widened from outside."""
    from seshat.integrations import guided_setup

    source = _code_only(guided_setup)
    for forbidden in ("sys.argv", "os.environ", "getenv", "argparse"):
        assert forbidden not in source, forbidden


def test_the_bridge_runs_no_subprocess_and_installs_nothing() -> None:
    """Invariant 7 (FR-015): execution is delegated, never re-implemented."""
    from seshat.integrations import guided_setup

    source = _code_only(guided_setup)
    # Call sites, not prose. The module's docstring legitimately says what it
    # does NOT do, so a bare "npm " substring matches documentation and pushes
    # the fix toward censoring the docs instead of the code -- the same
    # false-positive spec 153's boundary test names explicitly.
    for forbidden in (
        "import subprocess",
        "subprocess.run",
        "urlopen(",
        "pip install",
        "npm install",
        "git clone",
        "write_lock(",
        "shutil.",
    ):
        assert forbidden not in source, forbidden


def test_the_bridge_makes_no_approval_decision_of_its_own() -> None:
    """Invariant 6 (FR-012): authority is the committed gate's verdict alone.

    The bridge takes `approval_met` as an input it cannot compute. If it ever
    imports the gate and decides for itself, this fails -- which is the point:
    two places that can say yes is one place too many.
    """
    from seshat.integrations import guided_setup

    source = _code_only(guided_setup)
    for forbidden in (
        "from seshat.integrations.approval",
        "evaluate(",
        "ApprovalVerdict",
    ):
        assert forbidden not in source, forbidden


def test_the_cli_takes_authority_from_the_committed_gate_only() -> None:
    """Invariant 6 (FR-012): one authority source, and it reads HEAD."""
    from seshat.cli.commands import integrations

    source = _source(integrations)

    assert "from seshat.integrations.approval import evaluate" in source
    assert source.count("verdict.authorized") == 1


# --------------------------------------------------------------------------- #
# Invariant 8: the profile path is untouched.
# --------------------------------------------------------------------------- #


def test_the_default_profile_value_is_unchanged() -> None:
    """Invariant 8 (FR-020, SC-013): spec 144 FR-006 protects this value."""
    from seshat.integrations.catalog import ANALYTICS_FULL, DEFAULT_PROFILE
    from seshat.integrations_setup import DEFAULT_PROFILE as EXPORTED

    assert DEFAULT_PROFILE == ANALYTICS_FULL
    assert EXPORTED == ANALYTICS_FULL


def test_the_derived_selector_is_opt_in_and_defaults_off() -> None:
    """Invariant 8 (FR-020): the default journey is the profile journey."""
    import argparse

    from seshat.cli.parser_integrations import add_integrations_parser

    parser = argparse.ArgumentParser()
    add_integrations_parser(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["integrations", "setup"])

    assert args.derived is False
    assert args.profile


def test_a_profile_run_still_selects_and_labels_by_profile(tmp_path: Path) -> None:
    """Invariant 8 (FR-020): selection and the reported label are unchanged."""
    from seshat.integrations.catalog import profile_components
    from seshat.integrations.installer import plan

    (tmp_path / ".seshat").mkdir()
    outcome = plan(tmp_path, profile="analytics-core")
    planned = {row.component for row in outcome.rows}

    assert outcome.profile == "analytics-core"
    assert planned == {item.id for item in profile_components("analytics-core")}


def test_a_derived_run_reports_a_derived_selection_label(tmp_path: Path) -> None:
    """Invariant 10 (FR-019): a derived scope never claims a curated profile."""
    from seshat.integrations.catalog import component
    from seshat.integrations.installer import plan

    (tmp_path / ".seshat").mkdir()
    outcome = plan(tmp_path, components=(component("connectorx"),))

    assert outcome.profile == "derived"
    assert [row.component for row in outcome.rows] == ["connectorx"]


# --------------------------------------------------------------------------- #
# T048: secrets, and no platform-specific literal.
# --------------------------------------------------------------------------- #


def test_no_secret_appears_in_the_bridge_or_its_outputs() -> None:
    """T048 (FR-022, SC-014)."""
    from seshat.integrations import guided_setup

    source = _source(guided_setup).lower()
    for forbidden in ("password", "api_key", "postgresql://", "secret"):
        assert forbidden not in source, forbidden


def test_no_platform_specific_literal_in_the_bridge() -> None:
    """T048: a Windows literal would go vacuous on Linux CI."""
    from seshat.integrations import guided_setup

    source = _source(guided_setup)

    assert ".exe" not in source
    assert "\\\\" not in source
