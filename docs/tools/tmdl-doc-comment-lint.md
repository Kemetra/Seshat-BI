# TMDL doc-comment lint — `seshat tmdl-doc-comment-lint`

Checks **one** rule in a semantic model's TMDL: a `///` documentation block must
be followed by a declaration — never a blank line, never end-of-file (issue
#494).

**This is NOT a TMDL syntax validator.** A clean result means only that every
`///` block in the scanned files attaches to a following non-blank line. It says
nothing about whether the rest of the TMDL is valid, and **a pass does NOT mean
Power BI Desktop can load the model.** Do not report it as pre-Desktop
clearance, and do not report a model "validated" or "Desktop-ready" on the
strength of it.

```
seshat tmdl-doc-comment-lint --model <path/to/X.SemanticModel>
```

## The one rule, and why it is worth its own check

In TMDL a `///` block is *attached* documentation: it documents the object
declared on the very next line. A block followed by a blank line documents
nothing, and Desktop rejects the **entire project** rather than one object:

```
TMDL Format Error:
    Parsing error type - InvalidLineType
    Detailed error - Unexpected line type: Empty!
    Document - './relationships'
    Line Number - 5
...
InnerException0.PowerBINonFatalError_ErrorCode: DataModelLoadFailed
```

Nothing renders, and the actionable line is buried in a .NET stack trace. No
other check in this repo sees it: `seshat pbir-validate-bindings` resolves field
*references* against TMDL it has already parsed as data (it produced
byte-identical output before and after the defect in #494), and `parse_tmdl`
(`src/seshat/tmdl.py`) is an **extractor** — unrecognized lines fall through by
design — not a validator.

The mistake is easy for an agent to make precisely because documenting your work
is otherwise good practice, and it is invisible until Desktop.

## Scope — stated as a boundary, not a caveat

| Checked | Not checked |
|---|---|
| A `///` block is followed by a non-blank line | Any other TMDL syntax rule |
| A `///` block is not the last line of a file | Indentation, keywords, property names |
| Every `*.tmdl` under `definition/` (incl. `relationships.tmdl`) | Whether Desktop can load the model |
| Whitespace-only lines count as blank; CRLF and LF alike | DAX validity, bindings, refs, lineage |
| Genuine indented docs (a measure doc under its table) | `///` inside an embedded M/DAX expression body |

The output repeats this boundary on every run, including a passing one — that is
where over-reading happens.

### Embedded M/DAX bodies are excluded, deliberately

`///` is **also** a legal line comment in M and DAX — both start line comments
with `//`, so a third slash is just comment text — and an M `source =` body or a
multiline measure body may legitimately contain blank lines. Flagging such a line
would **block a valid model**, which for a brand-new lint is worse than the gap
it closes: an agent hitting it cannot tell a real defect from a lint bug, and the
rational response is to stop trusting the verb. Under-claiming beats blocking
valid input, so a `///` inside an expression body is not evaluated and this lint
makes no claim about it.

The exclusion is structural rather than a `//`-vs-`///` special case. TMDL is
indentation-based: a body is introduced by a line whose content **ends with `=`**
(`source =`, `measure Margin =`) and covers the following lines indented
**strictly deeper**. A blank line does **not** close a body — that is exactly the
M-body case — so a body closes at the first non-blank line indented at or
shallower than its introducer. `expression Server = "..."`, `annotation X = Y`
and `partition p = m` do not end with `=`, so they open no body. Genuine
**indented** documentation — a measure doc under its table, the shape this repo's
committed TMDL uses — is still fully checked.

## Why it is not named `tmdl-validate`

Because it does not validate TMDL. Issue #494's actual complaint was a check
whose surrounding prose promised more than the check performed, so a clean
result licensed a conclusion it could not support. A one-rule lint shipped under
a general-validation name would recreate that defect while appearing to fix it.
The name states the rule; the rule is what you get.

## Why the full fix is not here

Full-fidelity TMDL validation needs the
`Microsoft.AnalysisServices.Tabular.Tmdl` / `TmdlSerializer.DeserializeDatabase`
path that Desktop itself uses. [ADR 0001](../decisions/0001-tmdl-pbir-parser.md)
**deliberately excluded** TOM/`sempy` so the static governance core stays
headless — no Power BI Desktop, no .NET, no network, on any OS in CI. That
boundary is untouched here: this lint is pure stdlib text reading. Issue #494's
broader gap therefore remains open, and this lint does not close it.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | Every `///` block in the scanned files is followed by a non-blank line. **Not** Desktop clearance. |
| 1 | At least one unattached `///` block, **or** a fail-closed input problem: the model dir is missing, no `*.tmdl` was found under `definition/`, or a file could not be read. |

Fail-closed is deliberate: checking nothing must not look like checking
successfully.

## Output

```
status: blocked
[doc-comment-not-attached] powerbi/Demo.SemanticModel/definition/relationships.tmdl: /// documentation block ending at line 3 is followed by blank line 4; a /// block must attach directly to the object it documents
evidence: 1 TMDL document(s) checked for the ///-must-attach rule only
evidence: scope: ONE rule. This is NOT a TMDL syntax validator, and a pass does NOT mean Power BI Desktop can load the model.
scope: checks ONE rule -- that a /// documentation block is followed by a declaration, never a blank line or EOF. It is NOT a TMDL syntax validator: a pass does NOT mean the TMDL is valid or that Power BI Desktop can load the model.
note: this is a read-only lint report; it grants no approval and never sets a readiness stage.
```

The finding names the last `///` line of the block (the line to move or delete)
and the offending blank. Desktop reports the blank instead, so both are printed
and the two reports can be matched up.

A multi-line `///` run is one block and reports once, at its attachment point.
UTF-8 BOM is tolerated (`utf-8-sig`) — Power BI writes BOM, and a BOM must not
hide a violation on line 1, which is exactly where #494's defect sat.

## Read-only, grants no approval

The lint never writes a file and never sets a readiness stage. A clean result is
evidence for a named human, never an approval.
