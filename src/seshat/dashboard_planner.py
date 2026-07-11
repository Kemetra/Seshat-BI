"""Read-only Non-Duplicate Dashboard Planner (spec 116).

For ONE table + ONE caller-supplied PROPOSED dashboard idea, return exactly one
categorical verdict -- ``new`` / ``extends <page>`` / ``duplicate of <page>`` --
by reducing both the proposal and each committed page to its set of
``(business_question, bound_contract, dimension)`` tuples and computing a
DETERMINISTIC SET RELATIONSHIP over them. The match key is
``(bound_contract, dimension)`` compared by EXACT committed value; a dimension's
table qualifier is PRESERVED (``dim_product[category]`` and
``dim_customer[category]`` are distinct), while a bare free-text token
(``category``) still matches a committed field by its inner column name.

Comparison corpus: the target table's committed design directory
``mappings/<table>/design/`` -- ``dashboard-layout.md`` (page + business
questions), ``visual-list.md`` (visuals), and the authoritative
``visual-contract-binding-map.md`` (each visual -> approved contract + mapped
dimension). Cross-table dedup is OUT of scope (single-table, Clarification Q1).

Scope wall (load-bearing):
- WRITES NOTHING and opens NO connection. No file-write path exists here
  (structural, grep-verifiable), matching the shipped read-only surfaces
  ``approval_inbox`` / ``blocker_explainer`` / ``run_next``.
- Emits NO score, count, overlap percentage, confidence value, or ranking (hard
  rule #9). The verdict is set membership over committed tuples, never a number.
- Invents no page/visual/metric; classifies the proposal AS GIVEN (no
  enrichment). A proposal measure with no committed contract is adds-new.
- Adds NO ``retail check`` rule and is gate-agnostic: a ``new`` verdict is NOT
  clearance to build and NOT a ``dashboard_ready`` pass.
- Generic (Principle VII): per-table, no hardcoded table/page/contract/dimension.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_BINDING_MAP = "visual-contract-binding-map.md"
_VISUAL_LIST = "visual-list.md"
_LAYOUT = "dashboard-layout.md"

# Header substrings that identify each authoritative binding-map column. The
# tuple table is the one carrying BOTH a visual-id column and a contract column
# (this excludes the "contract coverage" table, which has approved_contract but
# no visual_id).
_H_ROW_ID = ("visual_id", "visual id")
_H_CONTRACT = ("bound_contract", "bound contract")
_H_QUESTION = ("business_question", "business question")
_H_FIELD = ("semantic_model_field", "field")
_H_PAGE = ("page",)


def _read_text(path: Path) -> str | None:
    """Read committed text (utf-8 tolerant of a BOM); None on any read failure."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _clean_dim(raw: str) -> str:
    """Clean a dimension reference, PRESERVING any table qualifier.

    ``dim_product_rss[category]`` -> ``dim_product_rss[category]`` (kept whole so
    two distinct fields sharing an inner column name are NOT conflated); a bare
    ``category`` -> ``category``. Only structural wrappers (backticks, surrounding
    whitespace) and trailing sentence punctuation from a free-text clause (e.g.
    ``category?`` -> ``category``) are stripped -- committed dimension tokens are
    punctuation-free identifiers, so this never over-strips them.
    """
    return raw.strip().strip("`").strip().strip(".,;:!?\"'").strip()


def _dim_match_tokens(dim: str) -> set[str]:
    """The forms a dimension matches on: its full qualified value ALWAYS, plus its
    bare inner token when qualified (``dim_product_rss[category]`` ->
    ``{dim_product_rss[category], category}``). This lets a bare free-text
    ``category`` match a committed qualified field by inner name, while a QUALIFIED
    proposal (e.g. ``dim_customer[category]``) matches only the exact committed
    field -- so distinct same-named columns are never conflated. A bare token
    cannot disambiguate two identically-named columns on the same contract; supply
    the qualifier to distinguish them.
    """
    tokens = {dim}
    inner = re.findall(r"\[([^\]]+)\]", dim)
    if inner:
        tokens.add(inner[-1].strip())
    return tokens


def _cells(line: str) -> list[str] | None:
    """Split a markdown table row into trimmed cells, or None if not a row."""
    if "|" not in line:
        return None
    raw = line.strip().strip("|").split("|")
    if len(raw) < 2:
        return None
    return [c.strip() for c in raw]


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= {"-", ":", " "} and c for c in cells)


def _header_index(headers: list[str], needles: tuple[str, ...]) -> int | None:
    for i, head in enumerate(headers):
        low = head.lower()
        if any(n in low for n in needles):
            return i
    return None


def _dimension_from_field(field_cell: str) -> str:
    """Extract the mapped dimension from a binding-map field cell.

    ``\\`[TotalSales]\\` by \\`dim_product_rss[category]\\``` -> ``category``.
    A card with no ``by`` clause (a headline aggregate) -> ``""`` (no slice).
    """
    match = re.search(r"\bby\b\s+`?([^`(]+)`?", field_cell)
    if not match:
        return ""
    return _clean_dim(match.group(1))


def _binding_rows(text: str) -> list[dict[str, str]]:
    """Parse the authoritative binding-map table into row dicts.

    Selects the FIRST markdown table whose header has both a visual-id column and
    a bound-contract column (excludes the contract-coverage / dropped-contract
    tables). Returns one dict per data row with page/row_id/question/contract/
    dimension. Tolerant of surrounding prose.
    """
    lines = text.splitlines()
    for start, line in enumerate(lines):
        headers = _cells(line)
        if headers is None:
            continue
        cols = {
            "id": _header_index(headers, _H_ROW_ID),
            "contract": _header_index(headers, _H_CONTRACT),
            "question": _header_index(headers, _H_QUESTION),
            "field": _header_index(headers, _H_FIELD),
            "page": _header_index(headers, _H_PAGE),
        }
        if cols["id"] is None or cols["contract"] is None:
            continue
        return _rows_after(lines[start + 1 :], cols)
    return []


def _cell_at(cells: list[str], idx: int | None) -> str:
    """Whitespace-trimmed cell at ``idx``; ``""`` if the column is absent."""
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx].strip()


def _col(cells: list[str], idx: int | None) -> str:
    """Like :func:`_cell_at` but also strips markdown backticks (id/page/contract)."""
    return _cell_at(cells, idx).strip("`").strip()


def _row_dict(cells: list[str], cols: dict[str, int | None]) -> dict[str, str]:
    return {
        "page": _col(cells, cols["page"]),
        "row_id": _col(cells, cols["id"]),
        "question": _cell_at(cells, cols["question"]),
        "contract": _col(cells, cols["contract"]),
        "dimension": _dimension_from_field(_cell_at(cells, cols["field"])),
    }


def _rows_after(lines: list[str], cols: dict[str, int | None]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        cells = _cells(line)
        if cells is None:
            break  # table ends at the first non-pipe line
        if _is_separator(cells):
            continue
        if not _col(cells, cols["contract"]):
            continue
        rows.append(_row_dict(cells, cols))
    return rows


def _subject_area(text: str | None) -> str:
    """The single-page name for a corpus without an explicit page column."""
    if text:
        match = re.search(r"subject_area:\s*`?([^`\n(]+)`?", text)
        if match:
            return match.group(1).strip()
    return "the committed page"


def _pages_from_rows(
    rows: list[dict[str, str]], default_page: str
) -> list[dict[str, Any]]:
    """Group binding rows into pages (by the page column, else one page)."""
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        name = row["page"] or default_page
        grouped.setdefault(name, []).append(row)
    pages: list[dict[str, Any]] = []
    for name in sorted(grouped):
        page_rows = grouped[name]
        keys = {
            (r["contract"], tok)
            for r in page_rows
            for tok in _dim_match_tokens(r["dimension"])
        }
        pages.append({"name": name, "keys": keys, "rows": page_rows})
    return pages


def _load_design_corpus(design_dir: Path, checked_path: str) -> dict[str, Any]:
    """Parse the committed design corpus into pages of tuple-sets.

    Never raises: a missing dir / OSError / unreadable binding map / empty table
    all yield ``present: False`` (``new by absence``); the checked path is always
    named (FR-007).
    """
    corpus: dict[str, Any] = {
        "present": False,
        "dir_exists": design_dir.is_dir(),
        "checked_path": checked_path,
        "pages": [],
    }
    binding_text = _read_text(design_dir / _BINDING_MAP)
    if binding_text is None:
        return corpus
    rows = _binding_rows(binding_text)
    if not rows:
        return corpus
    # Page ownership: the binding-map `page` column wins; else an explicit `page`
    # column in visual-list.md (joined by visual_id); else one page. `region` is
    # an INTRA-page zone, never a page key -- so a single executive page with
    # regions stays one page (no false cross-region split).
    _apply_page_ownership(rows, _visual_page_map(design_dir))
    default_page = _subject_area(_read_text(design_dir / _LAYOUT) or binding_text)
    corpus["pages"] = _pages_from_rows(rows, default_page)
    corpus["present"] = bool(corpus["pages"])
    return corpus


def _table_pairs(
    text: str, left: tuple[str, ...], right: tuple[str, ...]
) -> list[tuple[str, str]]:
    """(left, right) cell pairs from the FIRST table carrying both columns."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        headers = _cells(line)
        if headers is None:
            continue
        i_left = _header_index(headers, left)
        i_right = _header_index(headers, right)
        if i_left is None or i_right is None:
            continue
        return _pairs_after(lines[start + 1 :], i_left, i_right)
    return []


def _pairs_after(lines: list[str], i_left: int, i_right: int) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in lines:
        cells = _cells(line)
        if cells is None:
            break
        if _is_separator(cells):
            continue
        left, right = _col(cells, i_left), _col(cells, i_right)
        if left and right:
            pairs.append((left, right))
    return pairs


def _visual_page_map(design_dir: Path) -> dict[str, str]:
    """visual_id -> page from visual-list.md's explicit ``page`` column, if any.

    Region is intra-page and is NOT a page key; ``{}`` when no page column exists
    (the shipped single-page corpus), leaving grouping to the single-page default.
    """
    text = _read_text(design_dir / _VISUAL_LIST)
    if text is None:
        return {}
    return dict(_table_pairs(text, _H_ROW_ID, _H_PAGE))


def _apply_page_ownership(
    rows: list[dict[str, str]], ownership: dict[str, str]
) -> None:
    """Fill each row's page from visual-list ownership when the binding map's own
    ``page`` column left it empty (in place; binding-map page always wins)."""
    for row in rows:
        if not row["page"]:
            row["page"] = ownership.get(row["row_id"], "")


# --------------------------------------------------------------------------- #
# proposal reduction (classify AS GIVEN -- no enrichment, FR-006)
# --------------------------------------------------------------------------- #
def _proposal_tuple(
    question: str, contract: str, dimension: str, source: str
) -> dict[str, str]:
    return {
        "question": question.strip(),
        "contract": contract.strip(),
        "dimension": dimension.strip(),
        "dimension_key": _clean_dim(dimension),
        "source": source,
    }


def _tuples_from_free_text(description: str) -> list[dict[str, str]]:
    """Read ``<contract> by <dimension>`` clauses from free text, as given.

    Splits on ``,``/``;``/newline/`` and `` (so a one-tuple-per-line ``@file`` or
    pasted list is read in full, not just its first line) then reads a ``by``
    clause per clause. Reads ONLY what is tuple-shaped; infers no measure/dimension
    the caller did not state (the free-text edge case). Nothing tuple-shaped -> no
    tuple.
    """
    tuples: list[dict[str, str]] = []
    for clause in re.split(r"[,;\r\n]|\band\b", description):
        match = re.search(r"([A-Za-z_]\w*)\s+by\s+(.+)", clause.strip())
        if match:
            tuples.append(
                _proposal_tuple("", match.group(1), match.group(2), "free-text")
            )
    return tuples


def _reduce_proposal(proposal: dict[str, Any]) -> list[dict[str, str]]:
    """Reduce the caller-supplied proposal to tuples AS GIVEN (FR-006).

    Structured ``tuples`` (each ``(question, contract, dimension)``) are taken
    verbatim; free-text ``description`` contributes any ``<contract> by <dim>``
    clauses. Order preserved; the classifier invents nothing.
    """
    out: list[dict[str, str]] = []
    for entry in proposal.get("tuples") or []:
        question, contract, dimension = (list(entry) + ["", "", ""])[:3]
        if str(contract).strip():
            out.append(
                _proposal_tuple(
                    str(question), str(contract), str(dimension), "structured"
                )
            )
    out.extend(_tuples_from_free_text(proposal.get("description") or ""))
    return out


# --------------------------------------------------------------------------- #
# the set-relationship decision (FR-003/FR-004)
# --------------------------------------------------------------------------- #
def _key(tup: dict[str, str]) -> tuple[str, str]:
    return (tup["contract"], tup["dimension_key"])


def _cited_rows(
    page: dict[str, Any], shared: set[tuple[str, str]], source_file: str
) -> list[dict[str, str]]:
    cites = [
        {
            "page": page["name"],
            "row_id": row["row_id"],
            "contract": row["contract"],
            "dimension": row["dimension"],
            "source_file": source_file,
        }
        for row in page["rows"]
        if any(
            (row["contract"], tok) in shared
            for tok in _dim_match_tokens(row["dimension"])
        )
    ]
    return sorted(cites, key=lambda c: (c["row_id"], c["contract"], c["dimension"]))


def _added_tuples(
    proposal: list[dict[str, str]],
    page: dict[str, Any],
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Proposal tuples absent from the matched page, with cross-page coverage.

    One flat pass: skip tuples the page covers and de-dup repeats in the same
    guard (a proposal may repeat a tuple), preserving first-seen order.
    """
    added: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for tup in proposal:
        marker = _key(tup)
        if marker in page["keys"] or marker in seen:
            continue
        seen.add(marker)
        added.append(
            {
                "contract": tup["contract"],
                "dimension": tup["dimension"],
                "also_covered_on": _covered_elsewhere(marker, pages),
            }
        )
    return added


def _covered_elsewhere(
    marker: tuple[str, str], pages: list[dict[str, Any]]
) -> list[str]:
    """Names of committed pages (sorted) whose tuple-set covers ``marker``."""
    return sorted(p["name"] for p in pages if marker in p["keys"])


def _relate(
    page: dict[str, Any], proposal_keys: set[tuple[str, str]]
) -> tuple[str, set]:
    """Relationship of the proposal to ONE page: duplicate / extends / disjoint."""
    shared = proposal_keys & page["keys"]
    if not shared:
        return ("disjoint", shared)
    if proposal_keys <= page["keys"]:
        return ("duplicate", shared)
    return ("extends", shared)


def _strongest(
    candidates: list[tuple[dict[str, Any], set]],
) -> tuple[dict[str, Any], set]:
    """Pick the most-covered page; lexical page name breaks ties (no printed count)."""
    return max(candidates, key=lambda c: (len(c[1]), _neg_lex(c[0]["name"])))


def _neg_lex(name: str) -> tuple[int, ...]:
    """A key that makes the lexically-SMALLEST name win a max() tie."""
    return tuple(-ord(ch) for ch in name)


def _new_verdict(reason: str) -> dict[str, Any]:
    return {"verdict": "new", "reason": reason, "matched_page": None}


def _partition_pages(
    pages: list[dict[str, Any]], proposal_keys: set[tuple[str, str]]
) -> tuple[list, list]:
    """Split pages into duplicate-candidates and extends-candidates."""
    dup: list[tuple[dict[str, Any], set]] = []
    ext: list[tuple[dict[str, Any], set]] = []
    for page in pages:
        relation, shared = _relate(page, proposal_keys)
        if relation == "duplicate":
            dup.append((page, shared))
        elif relation == "extends":
            ext.append((page, shared))
    return dup, ext


def _decide(
    corpus: dict[str, Any],
    proposal: list[dict[str, str]],
    source_file: str,
) -> dict[str, Any]:
    if not corpus["present"]:
        return _new_verdict("absent")
    if not proposal:
        return _new_verdict("empty_proposal")

    proposal_keys = {_key(t) for t in proposal}
    pages = corpus["pages"]
    dup, ext = _partition_pages(pages, proposal_keys)

    if dup:
        page, shared = _strongest(dup)
        return {
            "verdict": "duplicate",
            "reason": "covered",
            "matched_page": page["name"],
            "matched_rows": _cited_rows(page, shared, source_file),
            "added_tuples": [],
        }
    if ext:
        page, shared = _strongest(ext)
        return {
            "verdict": "extends",
            "reason": "partial",
            "matched_page": page["name"],
            "matched_rows": _cited_rows(page, shared, source_file),
            "added_tuples": _added_tuples(proposal, page, pages),
        }
    return _new_verdict("disjoint")


def classify_proposal(
    repo_root: Path | str,
    table: str,
    proposal: dict[str, Any],
) -> dict[str, Any]:
    """Classify one proposal against one table's committed design corpus.

    Returns the verdict document (read-only; writes nothing). ``proposal`` is a
    mapping ``{"description": str, "tuples": [(question, contract, dimension)]}``.
    """
    root = Path(repo_root)
    design_dir = root / "mappings" / table / "design"
    checked_path = f"mappings/{table}/design/"
    source_file = f"{checked_path}{_BINDING_MAP}"

    corpus = _load_design_corpus(design_dir, checked_path)
    reduced = _reduce_proposal(proposal)
    decision = _decide(corpus, reduced, source_file)

    return {
        "table": table,
        "verdict": decision["verdict"],
        "reason": decision["reason"],
        "matched_page": decision["matched_page"],
        "matched_rows": decision.get("matched_rows", []),
        "added_tuples": decision.get("added_tuples", []),
        "proposal": [
            {
                "question": t["question"],
                "contract": t["contract"],
                "dimension": t["dimension"],
                "source": t["source"],
            }
            for t in reduced
        ],
        "corpus_present": corpus["present"],
        "checked_path": corpus["checked_path"],
        "read_only": True,
    }


# --------------------------------------------------------------------------- #
# render (ASCII, no glyphs, no numeric/overlap/ranking token -- FR-015)
# --------------------------------------------------------------------------- #
_HEADER = (
    "Is this dashboard idea new, or a repeat of a page you already have? This is a\n"
    "read-only triage: it compares the proposal against the committed design corpus\n"
    "by set membership. It writes nothing, grants no approval, and moves no stage.\n"
    "A `new` verdict is NOT clearance to build."
)


def _verdict_line(verdict: dict[str, Any]) -> str:
    kind = verdict["verdict"]
    page = verdict["matched_page"]
    if kind == "duplicate":
        return f"VERDICT: duplicate of `{page}`"
    if kind == "extends":
        return f"VERDICT: extends `{page}`"
    if verdict["reason"] == "absent":
        return (
            "VERDICT: new -- by absence -- no committed dashboard design found at "
            f"`{verdict['checked_path']}`"
        )
    if verdict["reason"] == "empty_proposal":
        return (
            "VERDICT: new -- nothing tuple-shaped could be read from the proposal "
            "(nothing to match)"
        )
    return "VERDICT: new -- no committed page covers this proposal"


def _tuple_label(contract: str, dimension: str) -> str:
    if dimension:
        return f"`{contract}` by `{dimension}`"
    return f"`{contract}` (headline, no slice)"


def _proposal_section(verdict: dict[str, Any]) -> list[str]:
    lines = ["", "## Proposal (as given)", ""]
    if not verdict["proposal"]:
        return lines + ["- (no tuple-shaped content could be read)"]
    for tup in verdict["proposal"]:
        lines.append(
            f"- {_tuple_label(tup['contract'], tup['dimension'])}  [{tup['source']}]"
        )
    return lines


def _matched_section(verdict: dict[str, Any]) -> list[str]:
    rows = verdict["matched_rows"]
    if not rows:
        return []
    lines = ["", "## Matched committed rows", ""]
    for row in rows:
        lines.append(
            f"- `{row['page']}` / `{row['row_id']}` -- "
            f"{_tuple_label(row['contract'], row['dimension'])} "
            f"(`{row['source_file']}`)"
        )
    return lines


def _added_section(verdict: dict[str, Any]) -> list[str]:
    added = verdict["added_tuples"]
    if not added:
        return []
    lines = [
        "",
        f"## Added by the proposal (absent from `{verdict['matched_page']}`)",
        "",
    ]
    for item in added:
        note = ""
        if item["also_covered_on"]:
            others = ", ".join(f"`{p}`" for p in item["also_covered_on"])
            note = f" -- also on {others}"
        lines.append(f"- {_tuple_label(item['contract'], item['dimension'])}{note}")
    return lines


def _render_text(verdict: dict[str, Any]) -> str:
    lines = [f"# Dashboard Planner -- {verdict['table']}", "", _HEADER, ""]
    lines.append(_verdict_line(verdict))
    lines += _proposal_section(verdict)
    lines += _matched_section(verdict)
    lines += _added_section(verdict)
    return "\n".join(lines) + "\n"


def render(verdict: dict[str, Any], fmt: str = "text") -> str:
    """Render the verdict as ASCII text (default) or a JSON document. Writes nothing."""
    if fmt == "json":
        import json

        return json.dumps(verdict, indent=2) + "\n"
    return _render_text(verdict)
