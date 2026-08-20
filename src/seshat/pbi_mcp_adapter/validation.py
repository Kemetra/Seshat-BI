"""Spec 149 -- post-write validation. A failure blocks and carries rollback.

Closes review finding C2, which had two independent halves and both mattered:

* **The wrong validator family.** FR-013 named "the ``seshat check`` R-family".
  That family (``rules/pbir.py``) is report-layer only: R1 iterates
  ``*.Report/definition.pbir`` and R2 ``*.Report/definition/report.json``.
  This feature mutates the **semantic model** (TMDL), which neither corpus
  contains -- so the named validator would examine zero bytes of the thing that
  changed and report clean. Semantic-model validation is ``seshat
  semantic-check``.
* **Silence read as success.** ``seshat semantic-check`` exits **0** on an empty
  corpus while printing "nothing was verified ... This is NOT a clean result"
  (measured). It ships the remedy -- ``--require-inputs`` makes that exit 1 --
  so this module always passes that flag. Belt and braces:
  :class:`ValidationOutcome` makes "validated" **unrepresentable** when nothing
  was examined, so a future validator that quietly examines nothing cannot be
  reported as a pass.

The invalid states this type refuses to hold:

  * ``passed`` with ``artifacts_examined == ()``  -> nothing was read
  * ``failed`` with ``rollback_guidance == ()``   -> a failure nobody can undo
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: Blocker ids, continuing the shipped ``PBIMCP-*`` scheme.
BLOCKER_VALIDATION_FAILED = "PBIMCP-VAL-01"
BLOCKER_READ_NOTHING = "PBIMCP-VAL-02"
BLOCKER_VALIDATOR_ERROR = "PBIMCP-VAL-03"

BLOCKER_DETAIL: dict[str, str] = {
    BLOCKER_VALIDATION_FAILED: "post-write validation reported findings",
    BLOCKER_READ_NOTHING: (
        "validation examined zero artifacts, so it verified nothing; silence "
        "from an empty corpus is not a pass"
    ),
    BLOCKER_VALIDATOR_ERROR: "the validator could not be run to completion",
}

#: A stalled or failed validator must not read as clean, so the subprocess gets
#: its own workload-sized bound rather than the short shared cap in
#: ``gitutil.run_subprocess`` (research R4: that helper's docstring explicitly
#: excludes execution runners).
VALIDATION_TIMEOUT_SECONDS = 300


class ValidationInvalid(ValueError):
    """A :class:`ValidationOutcome` was constructed in an impossible state."""


@dataclass(frozen=True)
class ValidationOutcome:
    """The post-write verdict on the touched artifacts.

    ``artifacts_examined`` is not decoration: it is what makes a vacuous pass
    impossible to express. A validator that read nothing yields ``()``, and the
    constructor then refuses to call the outcome passed.
    """

    checks_run: tuple[str, ...]
    artifacts_examined: tuple[str, ...]
    failed: tuple[str, ...]
    rollback_guidance: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def _failure_lacks_guidance(self) -> bool:
        """A failure the operator cannot undo is not an actionable result."""
        return bool(self.failed) and not self.rollback_guidance

    @property
    def _silence_without_a_read(self) -> bool:
        """No findings AND nothing examined -- silence, not a pass."""
        return not self.failed and not self.artifacts_examined and not self.blockers

    def __post_init__(self) -> None:
        if self._failure_lacks_guidance:
            raise ValidationInvalid(
                "a failed validation must carry rollback guidance (FR-014)"
            )
        if self._silence_without_a_read:
            raise ValidationInvalid(
                "an outcome with no findings AND no artifacts examined must carry "
                f"the {BLOCKER_READ_NOTHING} blocker: nothing was verified"
            )

    @property
    def passed(self) -> bool:
        """True only when something was examined and nothing failed.

        Both halves are required. Dropping the first is the vacuity C2 named.
        """
        return not self.failed and not self.blockers and bool(self.artifacts_examined)

    @property
    def blocking(self) -> bool:
        return bool(self.failed or self.blockers)

    def detail_for(self, blocker: str) -> str:
        return BLOCKER_DETAIL.get(blocker, blocker)


def rollback_guidance_for(target_path: str, backup_ref: str | None) -> tuple[str, ...]:
    """Concrete, copy-pasteable rollback steps for one target.

    Named commands rather than prose: guidance an operator has to translate is
    guidance they will get wrong under pressure.

    Both interpolated values are shell-quoted. A PBIP path with spaces -- routine
    on Windows -- otherwise splits into several pathspecs and the promised rollback
    fails exactly when it is needed. The ref is operator-supplied input, so
    unquoted it can carry a second command into guidance the operator is told to
    paste (Codex review, PR #659).
    """
    path = shlex.quote(target_path)
    if backup_ref:
        ref = shlex.quote(f"--source={backup_ref}")
        return (
            f"git restore {ref} -- {path}",
            f"git diff --stat {shlex.quote(backup_ref)} -- {path}   # confirm restored",
        )
    return (
        f"git restore -- {path}   # discard the write (tree was clean)",
        f"git status --short -- {path}   # confirm restored",
    )


def read_nothing_outcome(checks_run: tuple[str, ...]) -> ValidationOutcome:
    """The honest outcome when validation examined no artifacts.

    Blocking, not passing, and not a warning. This is the shape that stops
    'validated' from meaning 'nothing looked'.
    """
    return ValidationOutcome(
        checks_run=checks_run,
        artifacts_examined=(),
        failed=(),
        rollback_guidance=(),
        blockers=(BLOCKER_READ_NOTHING,),
    )


def _run_validator(
    repo_root: Path, args: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    """Run one offline validator as a child process.

    ``stdin=DEVNULL`` because the parent may itself be speaking MCP over stdio,
    where an inherited stdin deadlocks. Its own timeout, not the shared cap.
    """
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, no user string
        args,
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=VALIDATION_TIMEOUT_SECONDS,
        check=False,
        shell=False,
    )


def _target_was_examined(repo_root: Path, artifact: Path) -> bool:
    """Whether ``semantic-check`` actually examined this artifact.

    TWO conditions, because either alone is a fail-open:

    1. **Discovered.** ``_semantic_files`` is the command's OWN discovery, so the
       two cannot disagree about the corpus. It only yields tracked TMDL under
       ``*.SemanticModel/definition/``, while the committed allowlist accepts any
       contained path -- so a perfectly parseable target at ``models/x.tmdl`` is
       SKIPPED, and another discoverable input still makes the command exit 0.
    2. **Parseable.** ``parse_tmdl`` is the command's own extractor; it returns
       ``None`` for a file with no top-level ``table`` block, which
       ``semantic.py`` skips with ``continue``.

    Checking only (2) proves the file COULD be parsed, not that the subprocess
    looked at it -- the same fail-open one level in (Codex review, PR #659).

    Fails CLOSED throughout: an unreadable file or a discovery error is "not
    examined", never "examined and fine".
    """
    from seshat.cli.commands.semantic import _semantic_files
    from seshat.tmdl import parse_tmdl

    try:
        discovered = _semantic_files(Path(repo_root).resolve(), False)
    except (OSError, RuntimeError, ValueError):
        return False
    resolved = artifact.resolve()

    def _parseable(path: Path) -> bool:
        try:
            return parse_tmdl(path.read_text(encoding="utf-8-sig")) is not None
        except OSError:
            return False

    # A FOLDER target: the vendor binds and flushes a whole model directory
    # (research.md R8), so the authorized artifact can be a directory rather than
    # one file. Both conditions still hold, applied to its contents: at least one
    # DISCOVERED file inside the subtree must also be PARSEABLE. Requiring only
    # discovery would pass on a folder full of unparseable files; requiring only
    # parseability would not prove the subprocess looked inside.
    #
    # Fails CLOSED: an empty folder, or one whose files the command skips, is
    # "not examined".
    if artifact.is_dir():
        return any(
            _parseable(found)
            for found in discovered
            if found.resolve().is_relative_to(resolved)
        )

    if not any(found.resolve() == resolved for found in discovered):
        return False
    return _parseable(artifact)


@dataclass(frozen=True)
class _ValidationRun:
    """What one validation run is about: the artifact and how to report on it."""

    repo_root: Path
    artifact: Path
    target_path: str
    backup_ref: str | None
    checks_run: tuple[str, ...]


def _outcome_for(returncode: int, run: _ValidationRun) -> ValidationOutcome:
    """Turn one finished validator run into a verdict.

    Split from :func:`validate_semantic_model` so invoking the validator and
    judging its result read as two steps. Decides nothing about WHETHER to run --
    it is handed a returncode and reports what that plus the artifact prove.
    """
    target_path, backup_ref = run.target_path, run.backup_ref
    checks_run, artifact = run.checks_run, run.artifact
    if returncode != 0:
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(target_path,),
            failed=(f"semantic-check exit {returncode}",),
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_VALIDATION_FAILED,),
        )

    # Exit 0 is the validator's claim, not proof it looked at THIS file.
    if not _target_was_examined(run.repo_root, artifact):
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(),
            failed=(
                "the validator did not examine the target: it is not a "
                "parseable semantic-model artifact after the write",
            ),
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_READ_NOTHING,),
        )
    return ValidationOutcome(
        checks_run=checks_run,
        artifacts_examined=(target_path,),
        failed=(),
        rollback_guidance=(),
        blockers=(),
    )


def validate_semantic_model(
    repo_root: Path,
    *,
    target_path: str,
    backup_ref: str | None = None,
    runner: object = None,
) -> ValidationOutcome:
    """Validate the touched semantic model offline, after a write.

    Uses ``seshat semantic-check --require-inputs``: the semantic-model family,
    not the report-layer R-family, and with the flag that turns "no input
    discovered" from exit 0 into exit 1. ``runner`` is injectable so tests can
    drive every branch without a real subprocess.

    A zero exit is necessary but NOT sufficient. ``--require-inputs`` catches only
    an EMPTY corpus; it says nothing about whether *this* target was among the
    inputs actually parsed. ``semantic-check`` skips a ``*.tmdl`` that no longer
    holds a top-level ``table`` block, so a write which destroyed the target is
    silently absent from a "no drift" run. :func:`_target_was_examined` closes
    that gap by reading the artifact directly (Codex review, PR #659).
    """
    # RESOLVED, because the child gets both `cwd=root` and `--repo <root>`. With a
    # non-dot relative repo (`--repo ../project`) the child would re-resolve that
    # string from inside the repository and validate a different or nonexistent
    # directory -- reporting a good mutation as a validation failure and telling
    # the operator to roll it back (Codex review, PR #659).
    root = Path(repo_root).resolve()
    artifact = root / target_path
    checks_run = ("seshat semantic-check --require-inputs",)

    # An absent artifact means the write produced nothing to validate. Reported
    # honestly as read-nothing rather than as a clean run.
    #
    # A DIRECTORY is a legitimate target: the vendor binds and flushes a whole
    # TMDL folder (research.md R8), so `exists()` rather than `is_file()`.
    # Requiring a file here rejected every folder target before
    # `_target_was_examined` could inspect its contents (issue #660 review C1).
    if not artifact.exists():
        return read_nothing_outcome(checks_run)

    invoke = runner if runner is not None else _run_validator
    # The RUNNING interpreter, not whatever `python` resolves to on PATH. On the
    # documented pipx install -- or any system exposing only `python3` -- a bare
    # `python` is absent or lacks Seshat, so the validator would fail to start and
    # every apply would report a post-mutation validation failure with rollback
    # guidance for a write that was actually fine (Codex review, PR #659).
    args = (
        sys.executable,
        "-m",
        "seshat.cli",
        "semantic-check",
        "--repo",
        str(root),
        "--require-inputs",
    )
    try:
        completed = invoke(root, args)  # type: ignore[operator]
    except (subprocess.TimeoutExpired, OSError):
        return ValidationOutcome(
            checks_run=checks_run,
            artifacts_examined=(target_path,),
            failed=("validator did not complete",),
            rollback_guidance=rollback_guidance_for(target_path, backup_ref),
            blockers=(BLOCKER_VALIDATOR_ERROR,),
        )

    return _outcome_for(
        completed.returncode,
        _ValidationRun(root, artifact, target_path, backup_ref, checks_run),
    )
