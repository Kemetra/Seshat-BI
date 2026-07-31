"""`portability-audit-v1` -- a gate over shipping skill text.

Spec 138 User Story 3, `contracts/portability-audit.md`.

A skill that says "read `templates/source-map.yaml`" works perfectly in this
repository and, once bundled, instructs a consumer agent to open a path their
workspace has never contained. This module fails the export instead of shipping
that instruction.

It is a GATE, deliberately with no repair surface. Rewriting text at export time
would let a generated skill diverge silently from its canonical source, which is
the single-source property the whole design rests on (FR-018). A finding is
resolved by rewriting canonical text or by not shipping the skill -- never by
marking it, which is why no suppression mechanism exists.

**Classification is by intent, not by path.** A prefix rule would be wrong in both
directions: `templates/` is absent from a fresh workspace, so a prefix rule flags
legitimate scaffold-output references; and a genuinely broken reference under a
permitted prefix would pass. So an absent path fails *unless* the line carrying it
is one of the two exemptions the contract grants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from seshat import workspace_init

# A backtick-quoted, repo-relative-looking path. Spaces exclude command examples
# like `seshat scaffold`; the absence of `://` excludes URLs. A path must contain
# a separator, so bare identifiers such as `mcpServers` are not candidates.
_CANDIDATE = re.compile(r"`(?P<path>[A-Za-z0-9_.\-/<>*]+/[A-Za-z0-9_.\-/<>*]*)`")

# Ruled present 2026-07-31: `retail init` bootstraps this substrate, so a real
# consumer workspace has it even though `init-project` does not create it.
_BOOTSTRAP_PREFIX = ".seshat"

# Strips only leading `./` and `../` segments. `str.lstrip("./")` cannot be used:
# it strips every leading dot and slash, turning `.seshat/x` into `seshat/x` and
# silently defeating the dotted-prefix comparison below.
_LEADING_RELATIVE = re.compile(r"^(?:\.{1,2}/)+")

# Power BI defines this structure, not this repository: a saved PBIP model under
# the scaffolded `powerbi/` genuinely contains `definition/` and `.pbi/`. These
# names are therefore relative to a present directory, not repo-relative paths, and
# flagging them told users to fix references that were already correct.
_PBIP_INTERNAL = ("definition", ".pbi", ".platform")

# FR-017 exemption 1 -- `source-mapping` line 35 is the working precedent:
# "`templates/` exists only in the Seshat development repo".
_DEV_SCOPED = re.compile(r"in the Seshat development repo(sitory)?", re.IGNORECASE)

# FR-017 exemption 2, as narrowed by the owner ruling of 2026-07-31 ("name the
# scaffold verb"): a shipped skill names the verb that produces the file instead
# of instructing a read.
_SCAFFOLD_OUTPUT = re.compile(
    r"\b(writes|written|generates|generated|materializes|materialized|creating)\b",
    re.IGNORECASE,
)

# A versioned contract identifier (`seshat.binding-map/v1`) is a schema name, not a
# path. It has no extension and its last segment is a bare version marker.
_VERSION_ID = re.compile(r"^v\d+$", re.IGNORECASE)

# Only used to phrase the reason -- never to decide it. A provenance pointer is a
# finding too (the claim is fine, the path is not), so the verdict does not turn
# on whether a read verb is present.
_READ_VERB = re.compile(
    r"\b(read|open|see|consult|load|review|inspect|follow|refer to)\b",
    re.IGNORECASE,
)

_READ_REASON = (
    "read-instruction to a path a scaffolded workspace does not contain; name the "
    "scaffold verb that writes it, scope it to the development repository, or drop it"
)
_PROVENANCE_REASON = (
    "provenance pointer at a development-repository path; keep the claim and drop "
    "the path, or name the CLI verb the agent can actually invoke"
)


@dataclass(frozen=True)
class Finding:
    """One (skill, path, line) the export must reject, with the reason to fix it."""

    skill: str
    path: str
    line: int
    reason: str


def scaffolded_prefixes() -> tuple[str, ...]:
    """The workspace shape, read from `workspace_init` at call time.

    Obligation 5 forbids a duplicate list: if `init-project` starts scaffolding a
    new directory, this gate's notion of "present" must change with it and not
    drift behind a copy.

    `_BOOTSTRAP_PREFIX` is appended rather than added to `_EMPTY_DIRS`: the
    substrate is real in a consumer workspace but is written by a different verb,
    so `init-project`'s own surface stays exactly as specified.
    """
    return (*workspace_init._EMPTY_DIRS, _BOOTSTRAP_PREFIX)


def _normalise(path: str) -> str:
    return _LEADING_RELATIVE.sub("", path).rstrip("/")


def _is_bundled(path: str, bundled: frozenset[str], destination: str = "") -> bool:
    """Whether a path resolves to something the bundle itself carries.

    A shipped skill may legitimately point at its neighbours in the bundle: the
    knowledge-base wrappers reference `../../knowledge/<base>/INDEX.md`, which is
    correct in the delivered artifact and absent from the development repo's own
    scaffold. Presence is taken from the allowlist's DESTINATION paths, so the
    audit consumes the allowlist and never the reverse -- deriving the allowlist
    from the audit instead would make the two circular.
    """
    normalised = _normalise(path)
    # A skill's own subdirectories ship beside it, so `references/foo.md` resolves
    # against wherever THIS file lands. The destination is passed in rather than
    # guessed: knowledge bases land under `knowledge/<base>/` while kit skills land
    # under `skills/<name>/`, so a guessed prefix is right for one and wrong for
    # the other.
    candidates = [normalised]
    if destination:
        parent = PurePosixPath(destination).parent
        if str(parent) not in (".", ""):
            candidates.append(f"{parent}/{normalised}")
    return any(
        candidate == target or candidate.startswith(f"{target}/")
        for candidate in candidates
        for target in bundled
    )


def _is_present(path: str) -> bool:
    """Whether a scaffolded workspace can resolve this path.

    A path is present when it IS a scaffolded directory, sits UNDER one, or is an
    ANCESTOR of one. The ancestor case is not a nicety: `_EMPTY_DIRS` carries
    `warehouse/migrations`, so a bare `warehouse/` reference points at a directory
    the scaffold demonstrably creates, and flagging it would be a false finding.
    """
    normalised = _normalise(path)
    if not normalised:
        return True
    return any(
        normalised == prefix
        or normalised.startswith(f"{prefix}/")
        or prefix.startswith(f"{normalised}/")
        for prefix in scaffolded_prefixes()
    )


def _is_repo_path(path: str) -> bool:
    """Whether a backticked token is a repository path at all.

    Three classes of token look like paths and are not, each of which produced a
    false finding when the gate was first measured against the reviewed baseline:

    * a URL (`https://…`) -- not a workspace path;
    * a glob (`**/.pbi/localSettings.json`) -- a gitignore pattern, not something
      an agent is instructed to open;
    * a bare directory name (`definition/`, `.pbi/`) -- these describe structure
      *inside* a saved Power BI model folder, relative to `powerbi/`, so they are
      not repo-relative at all.

    Known narrow gap: this also drops a bare top-level directory such as
    `templates/`, so "read the files in `templates/`" would not be flagged. The one
    such reference in the reviewed set (finding 19) is dev-scoped and passes
    anyway, so no verdict changes -- but a *file* under a dev-only directory is
    still caught, which is the shape read-instructions actually take.
    """
    if "://" in path or "*" in path:
        return False
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if segments and segments[0] in _PBIP_INTERNAL:
        return False
    if segments and _VERSION_ID.match(segments[-1]):
        return False
    return len(segments) >= 2 and any(char.isalnum() for char in path)


def _logical_line(lines: list[str], index: int) -> str:
    """The wrapped sentence containing `lines[index]`.

    Markdown wraps freely, so an exemption phrase and the path it scopes routinely
    land on different physical lines -- "The committed record is written by that
    verb as" / "`orchestration/.../<run-id>.md`". Judging exemption per physical
    line rejected text that plainly named the writing verb.

    Walks backwards only while the previous line is an unfinished clause. A line
    ending in sentence-final punctuation or a table pipe is a boundary, so one
    bullet in a list cannot exempt its neighbours.
    """
    start = index
    while start > 0:
        previous = lines[start - 1].rstrip()
        if not previous or previous[-1] in ".!?|":
            break
        start -= 1
    return " ".join(lines[start : index + 1])


def _is_exempt(line: str) -> bool:
    """Whether this sentence scopes its references legitimately.

    A read verb BEATS a production verb. Matching obligation 3 on production verbs
    (`writes`, `generated`, `materialized`, …) rather than a closed list of phrases
    is what lets "the record is written by that verb as `…`" pass, but taken alone
    it would also exempt "read `docs/x.md`, generated last quarter" -- an
    instruction to open a path a consumer lacks, excused by an incidental word. So
    a sentence that instructs a read is never exempted by naming a producer.
    """
    if _DEV_SCOPED.search(line):
        return True
    if _READ_VERB.search(line):
        return False
    return bool(_SCAFFOLD_OUTPUT.search(line))


@dataclass(frozen=True)
class _Scope:
    """What one skill's references are judged against.

    These three values always travel together -- who is being audited, what the
    bundle carries, and where this file lands -- so they are one abstraction
    rather than three parameters threaded through every helper.
    """

    skill: str
    bundled: frozenset[str]
    destination: str

    def unresolvable(self, path: str) -> bool:
        """Whether this reference is one a shipped skill could not resolve."""
        if not _is_repo_path(path):
            return False
        if _is_present(path):
            return False
        return not _is_bundled(path, self.bundled, self.destination)


def _findings_in_line(scope: _Scope, line: str, number: int) -> list[Finding]:
    """Findings for one already-non-exempt line."""
    reason = _READ_REASON if _READ_VERB.search(line) else _PROVENANCE_REASON
    return [
        Finding(skill=scope.skill, path=path, line=number, reason=reason)
        for path in (m.group("path") for m in _CANDIDATE.finditer(line))
        if scope.unresolvable(path)
    ]


def audit_skill_text(
    skill: str,
    text: str,
    *,
    bundled_paths: frozenset[str] = frozenset(),
    destination: str = "",
) -> list[Finding]:
    """Every reference in `text` that a shipped skill could not resolve.

    `bundled_paths` are the allowlist's destination paths, so a skill may point at
    its neighbours inside the bundle. Left empty, the audit judges against the
    scaffolded workspace alone.

    An empty result means the text is permitted **unchanged** -- this function
    never returns modified content, because it never produces any.
    """
    scope = _Scope(skill=skill, bundled=bundled_paths, destination=destination)
    lines = text.splitlines()
    return [
        finding
        for number, line in enumerate(lines, start=1)
        if not _is_exempt(_logical_line(lines, number - 1))
        for finding in _findings_in_line(scope, line, number)
    ]
