"""Text rendering for `seshat next`'s two INFORMATIONAL guidance fields.

`agent_next` adds two additive, non-gating fields to the next-action document --
``source_map_shape_signpost`` (issue #488) and ``orchestration_checkpoint``
(issue #489). A key nothing renders is invisible to an agent reading
``--format agent`` text, so both must appear there.

Kept in its own module rather than inside ``commands/next.py``: that module already
owns two distinct rendering surfaces (the run-next response and the agent
document), and this is a third, independent concern with its own nested shape.
Separating it keeps each module focused (repo convention: many small files) and
keeps the guidance rendering testable on its own.

Every line this module emits is labelled INFORMATIONAL. That labelling is
load-bearing, not decorative: `next` neither adopts an adapter nor blocks on the
adapter choice, and the shape signpost is not a gate either -- so neither may read
like the next allowed action or a blocking reason.
"""

from __future__ import annotations

import re

_INFORMATIONAL = "INFORMATIONAL -- does not block"

# The assessor's reasoning lists, in the order a reader weighs them: what argues
# for the adapter, what argues against, and what only the human can answer.
_ADAPTER_REASON_LABELS: tuple[tuple[str, str], ...] = (
    ("for", "for"),
    ("against", "against"),
    ("open question", "open_questions"),
)


# An emitted install step must (a) survive the shell we tell the reader to use and
# (b) target the environment Seshat actually lives in. Two defects, both from PR #506
# review (P2), closed by one rewrite of the install head:
#
#   * QUOTING. POSIX sh needs the brackets quoted (glob metacharacters), but
#     `cmd.exe` passes apostrophes through LITERALLY, so
#     `pip install 'seshat-bi[dbt]'` reaches pip as `'seshat-bi[dbt]'` and is
#     rejected as an invalid requirement. DOUBLE quotes work in cmd.exe, PowerShell
#     and POSIX sh alike, and this repo's release lane is Windows.
#   * ENVIRONMENT. The validated install lane is pipx
#     (`docs/install/user-install.md`, `docs/install/agent-install.md`), which puts
#     Seshat in an ISOLATED environment. A bare `pip install` there targets the
#     AMBIENT interpreter, so the extra lands somewhere Seshat cannot see it -- or
#     the install is refused outright as externally-managed (PEP 668). The repo's
#     own agent-install.md documents the right command verbatim at line 26:
#     `pipx install "seshat-bi[dbt]"`. Emit exactly that, never an invented variant.
#
# Rewritten HERE, at the render boundary, not in `orchestration_assess`: that
# module's string is also consumed by `seshat orchestration-assess` and its wording
# is its own to own. This only ever touches an install step's head.
_PIP_INSTALL_EXTRA = re.compile(
    r"""\bpip\s+install\s+['"]?(seshat-bi\[[^\]'"]+\])['"]?"""
)


# A CALLABLE replacement, not a static template, because the emitted command names
# the extra's CONCRETE dependencies rather than the `seshat-bi[extra]` spec (#513).
#
# `pipx install --force "seshat-bi[dbt]"` -- the previous form -- re-resolves the
# UNPINNED `seshat-bi` requirement from the configured index, so enabling an extra
# silently replaced a candidate wheel / pinned / local build with whatever the index
# serves. `pipx inject seshat-bi --force <deps>` adds the dependencies without
# re-resolving the app, so the installed Seshat survives whatever its provenance.
# `--force` is still needed: without it pipx declines to modify an existing venv
# (the PR #510 finding, one level down). Same form `commands/dbt.py` already emits.
#
# Extras are resolved through `cli._extra_dependency_specs`, the ONE table shared
# with `cli._extra_install_hint`, so the two emitting surfaces cannot drift.
def _pipx_replacement(match: re.Match[str]) -> str:
    """`pip install seshat-bi[x]` -> the version-preserving pipx form."""
    from .. import _extra_dependency_specs

    spec = match.group(1)  # e.g. `seshat-bi[dbt]`
    extra = spec[spec.index("[") + 1 : spec.rindex("]")]
    specs = _extra_dependency_specs(extra)
    if not specs:
        # An extra with no known dependency table: keep the previous form rather
        # than emit an `inject` with no packages, which would do nothing silently.
        return f'pipx install --force "{spec}"'
    injected = " ".join(f'"{dep}"' for dep in specs)
    return f"pipx inject seshat-bi --force {injected}"


def _portable_quoting(step: str) -> str:
    """Rewrite an install step to the documented, shell-portable pipx form.

    Idempotent: an already-rewritten step is unchanged, because the pattern requires
    a ``pip install`` head and neither ``pipx install`` nor ``pipx inject`` matches
    it. Steps with no install head pass through untouched.
    """
    return _PIP_INSTALL_EXTRA.sub(_pipx_replacement, step)


def _opt_in_step_lines(note: dict) -> list[str]:
    """The opt-in sequence, one numbered STEP per line.

    ``orchestration_assess``'s ``opt_in_command`` is deliberately a prose
    composite -- e.g. ``pip install 'seshat-bi[dbt]'  (then: seshat dbt init;
    seshat dbt doctor)`` -- because adopting an adapter is a SEQUENCE, not one
    command. Labelling that whole value "opt in with" presented it as a single
    pasteable command, and pasting it fails at the parenthesized ``(then: ...)``
    (PR #506 review, P2). Splitting the prose here keeps each line individually
    runnable without rewriting the engine's string (its wording is the engine's to
    own). If the composite ever loses its ``(then: ...)`` shape this degrades to a
    single step -- never to a wrong one.

    When the document says STOP, ``opt_in_deferred`` is set and the value is the
    deferral sentence, not a command: it is rendered as prose under a ``deferred``
    label, and NO numbered step is emitted. Nothing runnable appears below a STOP
    (PR #506 review, P1).
    """
    value = note["opt_in_command"]
    if note.get("opt_in_deferred"):
        return [f"      opt-in steps deferred: {value}"]
    head, _, tail = value.partition("(then:")
    steps = [head.strip()]
    if tail:
        steps += [part.strip() for part in tail.rstrip(") ").split(";") if part.strip()]
    return [
        f"      opt-in step {number}: {_portable_quoting(step)}"
        for number, step in enumerate(steps, start=1)
        if step
    ]


def _adapter_note_lines(note: dict) -> list[str]:
    """One adapter's categorical verdict plus the assessor's own reasoning."""
    lines = [f"    {note['adapter']}: {note['recommendation']}  ({note['role']})"]
    for label, key in _ADAPTER_REASON_LABELS:
        for item in note.get(key, []):
            lines.append(f"      {label}: {item}")
    lines.extend(_opt_in_step_lines(note))
    return lines


def signpost_lines(signpost: str | None) -> list[str]:
    """Issue #488: name the canonical source-map shape while the map is written."""
    if not signpost:
        return []
    return [f"source_map_shape_signpost ({_INFORMATIONAL}): {signpost}"]


def orchestration_checkpoint_lines(checkpoint: dict | None) -> list[str]:
    """Issue #489: the adapter choice, with the tool's own recommendation."""
    if not checkpoint:
        return []
    lines = [
        f"orchestration_checkpoint ({_INFORMATIONAL}):",
        f"  stage: {checkpoint['stage']}",
        f"  decision_owner: {checkpoint['decision_owner']}",
        f"  recommended_action: {checkpoint['recommended_action']}",
        "  adapters:",
    ]
    for note in checkpoint["adapters"]:
        lines.extend(_adapter_note_lines(note))
    lines.append(f"  decision_rule: {checkpoint['decision_rule']}")
    if checkpoint.get("steps_deferred_by_block"):
        # Blocked: the checkpoint carries no command at all, so render none. The
        # verdict above stays visible; nothing runnable appears below the STOP.
        return lines
    lines.append(f"  full assessment: {checkpoint['full_assessment_command']}")
    # The workspace is named as DATA, on its own line -- never interpolated into the
    # command above, which stays `--repo .` and so needs no shell quoting.
    lines.append(f"  run commands in: {checkpoint.get('repo_path')}")
    lines.append(f"  command_scope: {checkpoint['command_scope']}")
    return lines


def guidance_lines(document: dict) -> list[str]:
    """Both guidance surfaces, in document order. Empty when neither applies."""
    return signpost_lines(document.get("source_map_shape_signpost")) + (
        orchestration_checkpoint_lines(document.get("orchestration_checkpoint"))
    )
