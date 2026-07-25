"""ONE TMDL lint rule: a ``///`` documentation block must attach to a declaration.

WHAT THIS IS -- AND EMPHATICALLY IS NOT
--------------------------------------
This module checks **one** rule and nothing else: the line immediately after a
contiguous run of ``///`` documentation lines must not be blank and must not be
end-of-file. In TMDL a ``///`` block is *attached* documentation -- it documents
the object declared on the very next line. A block followed by a blank line
documents nothing, and Power BI Desktop refuses to load the **entire** project:

    Parsing error type - InvalidLineType
    Detailed error - Unexpected line type: Empty!
    Document - './relationships'
    Line Number - 5

That whole-project ``DataModelLoadFailed`` is what this lint exists to catch
(issue #494).

It is **NOT a TMDL syntax validator.** A clean result from this lint means only
that every ``///`` block in the scanned files is followed by a non-blank line.
It says nothing about whether any other line is valid TMDL, and a clean result
is **NOT** clearance to open Power BI Desktop -- Desktop may still refuse to
load the model for any of the many reasons this lint does not look at. Do not
present it as a pre-Desktop gate.

WHY THE NARROW SCOPE IS DELIBERATE
----------------------------------
Full-fidelity TMDL validation needs the ``TmdlSerializer``/TOM path that
ADR 0001 (``docs/decisions/0001-tmdl-pbir-parser.md``) **deliberately excluded**
so this toolchain stays headless -- no Power BI Desktop, no .NET, no network, on
any OS. That boundary is untouched here: this lint is pure stdlib text reading.
The narrow name is load-bearing. A check named for general TMDL validation, that
in fact covers one rule, would recreate exactly the over-claim that issue #494
reported -- a clean report read as "Desktop will load this".

WHY THE PREDICATE IS BLANK-OR-EOF, NOT "IS A DECLARATION"
---------------------------------------------------------
Asserting the next line is a *valid object declaration* would require an
allowlist of TMDL keywords, which would false-positive on legitimate TMDL the
allowlist has not seen -- turning a narrow lint into a half-built general
validator that fails closed on valid input. Blank-or-EOF is what Desktop itself
reported (``Unexpected line type: Empty!``) and it cannot false-positive on a
declaration keyword nobody enumerated.

WHY EMBEDDED M/DAX BODIES ARE EXCLUDED (a deliberate narrowing)
---------------------------------------------------------------
``///`` is ALSO a legal line comment in M and DAX -- those languages start line
comments with ``//``, so a third slash is just part of the comment text -- and
an M ``source =`` body or a multiline measure body may legitimately contain
blank lines. Treating such a line as TMDL documentation would BLOCK A VALID
MODEL, which for a brand-new lint is worse than the gap it closes: an agent
hitting it cannot tell a real defect from a lint bug, and the rational response
is to stop trusting the verb. So a ``///`` inside an expression body is NOT
evaluated, and this lint makes NO claim about it.

The exclusion is structural, not a ``//``-vs-``///`` special case. TMDL is
indentation-based: an expression body is introduced by a line whose content ends
with ``=`` (``source =``, ``measure Margin =``) and consists of the following
lines indented STRICTLY DEEPER than that introducer. A blank line does NOT close
a body -- that is exactly the M-body case -- so a body closes only at the next
NON-BLANK line indented at or shallower than its introducer. Note this correctly
opens no body for ``expression Server = "..."``, ``annotation X = Y`` or
``partition p = m``: those do not END with ``=``. Genuine INDENTED documentation
(a measure doc under its table, the shape this repo's committed TMDL uses) is
still checked -- only the inside of an expression body is skipped.

This module is separate from ``seshat.tmdl`` on purpose: ``parse_tmdl`` there is
an EXTRACTOR (unrecognized lines fall through by design), not a validator, and
conflating the two is the confusion #494 is about.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# A TMDL documentation line. TMDL allows leading indentation (a measure's block
# is indented under its table), so the marker is matched after stripping.
_DOC_MARKER = "///"

# Read with utf-8-sig: Power BI writes UTF-8-with-BOM, and a BOM on line 1 would
# otherwise hide a violation in the very position issue #494 reported -- a
# ``///`` block at the TOP of the file (ADR 0001 records the same reason for
# reading PBIR JSON as utf-8-sig).
_ENCODING = "utf-8-sig"

#: The single finding class this lint can emit. Named for the rule, not for TMDL
#: generally, so a reader cannot mistake it for a syntax-error class.
FINDING_DOC_COMMENT_NOT_ATTACHED = "doc-comment-not-attached"


@dataclass(frozen=True)
class DocCommentFinding:
    """One unattached ``///`` block."""

    #: Path as given to the linter, POSIX-normalized for stable output.
    document: str
    #: 1-based line number of the LAST ``///`` line of the block -- the line the
    #: author must move or delete. Desktop reports the offending blank instead;
    #: both are printed so the two reports can be matched up.
    doc_line: int
    #: 1-based line number of the offending blank line, or ``None`` at EOF.
    blank_line: int | None
    kind: str = FINDING_DOC_COMMENT_NOT_ATTACHED

    @property
    def message(self) -> str:
        where = (
            "end of file"
            if self.blank_line is None
            else f"blank line {self.blank_line}"
        )
        return (
            f"/// documentation block ending at line {self.doc_line} is followed by "
            f"{where}; a /// block must attach directly to the object it documents"
        )


@dataclass(frozen=True)
class DocCommentLintResult:
    """Roll-up over the scanned files. ``status`` is ``pass`` or ``blocked``."""

    status: str
    findings: tuple[DocCommentFinding, ...] = ()
    files_scanned: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    #: Always False. This lint is evidence for a human, never an approval, and
    #: there is no field or method by which it can become one.
    grants_approval: bool = False


def _is_blank(line: str) -> bool:
    """A line Desktop would call ``Empty!``: whitespace-only counts, because tabs
    and spaces are TMDL indentation, not content.

    Line terminators never reach here: ``lint_text`` splits with
    ``str.splitlines()``, which consumes ``\\n``, ``\\r\\n`` and ``\\r`` alike, so
    a CRLF file (normal in this repo) is handled without special-casing.
    """
    return not line.strip()


def _indent_width(line: str) -> int:
    """Leading-whitespace width. Tabs count as one, which is enough: the only
    comparison made is against another line's width in the SAME file, and TMDL
    writers do not mix tabs and spaces within one nesting level."""
    return len(line) - len(line.lstrip())


def embedded_body_lines(lines: list[str]) -> frozenset[int]:
    """Indices of lines sitting INSIDE an embedded M/DAX expression body.

    A body opens on a line whose content ends with ``=`` (``source =``,
    ``measure X =``) and covers the following lines indented strictly deeper.
    A blank line does NOT close a body -- M bodies legitimately contain blanks,
    and closing on one is precisely the false positive this exists to prevent.
    A body closes at the first NON-BLANK line indented at or shallower than its
    introducer.

    Ambiguity is biased toward still-inside-body on purpose: exiting a body too
    early re-arms the false positive (blocking a valid model), while staying in
    one line too long only skips a check this lint already disclaims.
    """
    inside: set[int] = set()
    body_indent: int | None = None
    for index, line in enumerate(lines):
        if body_indent is not None:
            if not line.strip():
                # Blank lines are transparent: they neither close the body nor
                # get recorded (nothing checks a blank line directly).
                continue
            if _indent_width(line) > body_indent:
                inside.add(index)
                continue
            body_indent = None  # dedented to introducer depth or shallower
        stripped = line.rstrip()
        if stripped.strip() and stripped.endswith("="):
            body_indent = _indent_width(line)
    return frozenset(inside)


def lint_text(text: str, *, document: str) -> tuple[DocCommentFinding, ...]:
    """Return every unattached ``///`` block in ``text``.

    Pure function over already-read text: no filesystem, no network, no
    execution. Only the LAST ``///`` line of a contiguous run is considered --
    a multi-line block is one block, so one violation is reported once.
    ``///`` lines inside an embedded M/DAX expression body are skipped, where
    ``///`` is a legal line comment rather than TMDL documentation.
    """
    lines = text.splitlines()
    in_body = embedded_body_lines(lines)
    findings: list[DocCommentFinding] = []
    for index, line in enumerate(lines):
        if index in in_body:
            continue
        if not line.strip().startswith(_DOC_MARKER):
            continue
        following = lines[index + 1] if index + 1 < len(lines) else None
        if following is not None and following.strip().startswith(_DOC_MARKER):
            # Mid-block: the run continues, so this is not the attachment point.
            continue
        if following is None:
            findings.append(
                DocCommentFinding(
                    document=document, doc_line=index + 1, blank_line=None
                )
            )
        elif _is_blank(following):
            findings.append(
                DocCommentFinding(
                    document=document, doc_line=index + 1, blank_line=index + 2
                )
            )
    return tuple(findings)


def collect_tmdl_files(model_dir: Path) -> tuple[Path, ...]:
    """Every ``*.tmdl`` under ``model_dir/definition/``, sorted for determinism.

    The whole ``definition/`` tree, NOT just ``definition/tables/``: the defect
    in issue #494 was in ``definition/relationships.tmdl``, and a tables-only
    walk is precisely why the existing checks missed it.
    """
    definition = model_dir / "definition"
    if not definition.is_dir():
        return ()
    return tuple(sorted(definition.rglob("*.tmdl")))


def lint_model(model_dir: Path) -> DocCommentLintResult:
    """Lint every TMDL document under ``model_dir/definition/``.

    Fails closed: a missing ``definition/`` tree or a TMDL file that cannot be
    read is ``blocked``, never a quiet pass -- an unreadable input must not look
    like a clean one.
    """
    if not model_dir.is_dir():
        return DocCommentLintResult(
            status="blocked",
            evidence=(f"model directory not found: {_display(model_dir)}",),
        )
    paths = collect_tmdl_files(model_dir)
    if not paths:
        return DocCommentLintResult(
            status="blocked",
            evidence=(
                f"no *.tmdl found under {_display(model_dir / 'definition')}; "
                "nothing was checked, so this is not a pass",
            ),
        )
    findings: list[DocCommentFinding] = []
    unreadable: list[str] = []
    scanned: list[str] = []
    for path in paths:
        document = _display(path)
        try:
            text = path.read_text(encoding=_ENCODING)
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"could not read {document}: {exc}")
            continue
        scanned.append(document)
        findings.extend(lint_text(text, document=document))
    evidence = [
        f"{len(scanned)} TMDL document(s) checked for the ///-must-attach rule only",
        "scope: ONE rule. This is NOT a TMDL syntax validator, and a pass does "
        "NOT mean Power BI Desktop can load the model.",
        "scope: `///` inside an embedded M/DAX expression body is NOT checked -- "
        "it is a legal line comment there, not TMDL documentation.",
        *unreadable,
    ]
    status = "blocked" if findings or unreadable else "pass"
    return DocCommentLintResult(
        status=status,
        findings=tuple(findings),
        files_scanned=tuple(scanned),
        evidence=tuple(evidence),
    )


def _display(path: Path) -> str:
    """POSIX-style path text so output is identical on Windows and POSIX."""
    return path.as_posix()


def tmdl_doc_comment_lint_main(args: object) -> int:
    """CLI entry: ``seshat tmdl-doc-comment-lint``.

    Read-only. Exit 0 = every ``///`` block in the scanned files attaches to a
    following non-blank line. Exit 1 = at least one unattached block, or a
    fail-closed input problem. Exit 0 is NOT clearance to open Desktop and
    grants no approval.
    """
    result = lint_model(Path(args.model))  # type: ignore[attr-defined]
    print(f"status: {result.status}")
    for finding in result.findings:
        print(f"[{finding.kind}] {finding.document}: {finding.message}")
    for line in result.evidence:
        print(f"evidence: {line}")
    print(
        "scope: checks ONE rule -- that a /// documentation block is followed by "
        "a declaration, never a blank line or EOF. It is NOT a TMDL syntax "
        "validator: a pass does NOT mean the TMDL is valid or that Power BI "
        "Desktop can load the model."
    )
    print(
        "scope: /// inside an embedded M or DAX expression body is deliberately "
        "NOT checked -- /// is a legal line comment in those languages, so "
        "flagging it would block a valid model."
    )
    print(
        "note: this is a read-only lint report; it grants no approval and never "
        "sets a readiness stage."
    )
    return 1 if result.status == "blocked" else 0
