# Theme-compile-from-tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic `retail theme-compile` verb that reads a committed design-tokens YAML and writes its matching Power BI `theme.json`, reusing the existing theme renderer so the output is byte-identical to what `theme-gen` produced.

**Architecture:** One thin new module `src/seshat/theme_compile.py` reconstructs a `palette` dict and a `ThemeSeed` **purely from values already committed in the tokens YAML**, then delegates to the existing `theme_gen.render_theme_json`. It chooses no color and invents no rendering. A new `theme-compile` CLI subcommand dispatches to it. The existing DL3 (fidelity) and DL1 (purity) rules already check the written pair — no new rule.

**Tech Stack:** Python 3.13, stdlib only (`json`, `re`, `sys`, `pathlib`) + `PyYAML` (already a dependency, imported lazily like DL3 does) + the existing `retail.color` and `retail.theme_gen` modules. pytest (`@pytest.mark.unit`).

## Global Constraints

- **DEFINE-only.** Writes exactly one `themes/<name>.theme.json`. No PBIR, no `visual.json`, no model, no live Power BI, no network, no pbi-cli.
- **No color decision.** Every value written is copied from the committed tokens; the verb chooses nothing. Zero Principle-V color surface.
- **No self-granted pass** (rule #9 / Principle V). The verb reports where it wrote and that DL3/DL1 + Desktop validation still gate the theme; it never claims the theme is "good"; it emits no `score:`/`confidence:`.
- **No new rule, no new template, no ADR.** This is the same surface-3 `themes/*.theme.json` artifact `theme-gen` already produces.
- **Clean errors only.** Every failure path raises `ThemeCompileError` (caught at the CLI boundary → `stderr` + exit code 2), never a traceback.
- **Reuse, do not re-derive.** Use `theme_gen.render_theme_json`, `check_contrast_or_raise`, `is_valid_hex` (via `retail.color`), and the `_validate_name` slug guard. Do NOT copy their logic.
- **Encoding.** Write `theme.json` with `encoding="utf-8", newline="\n"` (matches `theme_gen.generate`). Read tokens with `encoding="utf-8-sig"` (matches DL3).
- **Naming.** Commit messages `<type>: <description>`. Never `--no-verify`. Work on branch `feat/theme-compile-from-tokens` (already checked out).

---

## File Structure

- **Create `src/seshat/theme_compile.py`** — the whole feature. Responsibilities: parse tokens YAML → `palette` + `ThemeSeed`; validate; delegate to `render_theme_json`; write with overwrite guard; a `theme_compile_main(args)` CLI entry. One clear purpose; ~120 lines.
- **Modify `src/seshat/cli.py`** — add the `theme-compile` subparser (near the `theme-gen` parser, ~line 205) and its dispatch branch (near the `theme-gen` dispatch, ~line 470).
- **Create `tests/unit/test_theme_compile.py`** — module-level tests (round-trip byte-identity, palette rebuild, error paths, overwrite guard).
- **Create `tests/unit/test_theme_compile_cli.py`** — CLI-level tests (exit 0 on success, exit 2 on bad tokens), mirroring `test_theme_gen_cli.py`.

---

### Task 1: The `theme_compile` module — palette rebuild + compile core

**Files:**
- Create: `src/seshat/theme_compile.py`
- Test: `tests/unit/test_theme_compile.py`

**Interfaces:**
- Consumes (from `retail.theme_gen`, existing, unchanged):
  - `ThemeSeed` — frozen dataclass; fields `name, mode, accent, background, text_primary, text_secondary, text_muted, data_colors, good, neutral, bad`.
  - `render_theme_json(palette: dict, seed: ThemeSeed) -> str` — reads `palette["colors"]` for all colors and `seed.name` only.
  - `check_contrast_or_raise(palette: dict, floor: float = AA_FLOOR) -> None` — raises `ThemeGenError` on sub-AA text contrast.
  - `_validate_name(name: str) -> None` — raises `ThemeGenError` on a non-slug name.
  - `_DEFAULT_SENTIMENT: dict` — fallback sentiment colors.
- Consumes (from `retail.color`, existing): `is_valid_hex(s: str) -> bool`.
- Produces (for Task 2 and tests):
  - `class ThemeCompileError(Exception)`.
  - `palette_from_tokens(tokens_doc: dict) -> dict` — returns `{"colors": {...}}` in `build_palette`'s shape.
  - `seed_from_tokens(tokens_doc: dict, name_override: str | None) -> ThemeSeed`.
  - `compile_theme(tokens_path: Path, out_path: Path | None, force: bool) -> Path` — returns the written path.

- [ ] **Step 1: Write the failing test for `palette_from_tokens`**

```python
# tests/unit/test_theme_compile.py
"""Unit tests for the tokens->theme compiler (retail.theme_compile)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from retail.theme_compile import (
    ThemeCompileError,
    compile_theme,
    palette_from_tokens,
    seed_from_tokens,
)

pytestmark = pytest.mark.unit

# A committed-tokens doc in the exact shape render_tokens_yaml writes.
TOKENS = {
    "meta": {
        "name": "executive-dark-design-tokens",
        "style": "generated (dark)",
        "version": "1",
        "compiles_to": "themes/executive-dark.theme.json",
    },
    "colors": {
        "primary": "#2FB6C4",
        "secondary": "#7BD6DF",
        "background": "#12263A",
        "text": {"primary": "#F2F6FA", "secondary": "#C4D1DE", "muted": "#93A6B8"},
        "sentiment": {"success": "#2E7D5B", "warning": "#B5832A", "danger": "#B23A3A"},
        "data_colors": ["#A5E3E9", "#7BD6DF", "#52C9D6", "#2FB7C5", "#25919C", "#1C6B73"],
    },
}


def test_palette_from_tokens_copies_every_color_field():
    pal = palette_from_tokens(TOKENS)
    c = pal["colors"]
    assert c["primary"] == "#2FB6C4"
    assert c["background"] == "#12263A"
    assert c["text"]["muted"] == "#93A6B8"
    assert c["sentiment"]["success"] == "#2E7D5B"
    assert c["data_colors"] == TOKENS["colors"]["data_colors"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py::test_palette_from_tokens_copies_every_color_field -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.theme_compile'`.

- [ ] **Step 3: Write the module — docstring, error, and `palette_from_tokens`**

```python
# src/seshat/theme_compile.py
"""Tokens -> theme compiler (DEFINE-only).

Reconstructs a Power BI ``theme.json`` from a *committed* design-tokens YAML by
rebuilding the palette from the tokens' own values and delegating to the existing
``theme_gen.render_theme_json`` -- the single source of the theme's JSON shape.
It chooses no color, derives nothing, and invents no key: every value written is
copied from the tokens. The output is byte-identical to what ``theme-gen`` wrote
for those tokens, which is precisely the invariant DL3 (token->theme fidelity)
asserts. This is the GENERATOR whose output DL3 checks; it removes the hand-edit
that is otherwise the only way to desync a theme from its tokens.

DEFINE-only: writes one ``themes/*.theme.json``; no PBIR/visual.json/model, no
pbi-cli / live Power BI / network. Reuses ``theme_gen``'s renderer, contrast gate,
and name-slug guard; ``retail.color`` for hex validation. Never self-grants a
readiness pass and emits no score (rule #9 / Principle V).
"""

from __future__ import annotations

import sys
from pathlib import Path

from .color import is_valid_hex
from .theme_gen import (
    _DEFAULT_SENTIMENT,
    ThemeSeed,
    _validate_name,
    check_contrast_or_raise,
    render_theme_json,
)


class ThemeCompileError(Exception):
    """A compile input/output problem surfaced cleanly (never a traceback)."""


_TOKENS_NAME_SUFFIX = "-design-tokens"


def palette_from_tokens(tokens_doc: dict) -> dict:
    """Rebuild build_palette's output shape purely from committed token values."""
    if not isinstance(tokens_doc, dict):
        raise ThemeCompileError("tokens document is not a mapping")
    colors = tokens_doc.get("colors")
    if not isinstance(colors, dict):
        raise ThemeCompileError("tokens missing required field: colors")
    text = colors.get("text")
    sentiment = colors.get("sentiment")
    if not isinstance(text, dict):
        raise ThemeCompileError("tokens missing required field: colors.text")
    if not isinstance(sentiment, dict):
        raise ThemeCompileError("tokens missing required field: colors.sentiment")
    dc = colors.get("data_colors")
    if not isinstance(dc, list) or not dc:
        raise ThemeCompileError(
            "tokens missing a non-empty colors.data_colors list"
        )
    fields = {
        "colors.primary": colors.get("primary"),
        "colors.secondary": colors.get("secondary"),
        "colors.background": colors.get("background"),
        "colors.text.primary": text.get("primary"),
        "colors.text.secondary": text.get("secondary"),
        "colors.text.muted": text.get("muted"),
        "colors.sentiment.success": sentiment.get("success"),
        "colors.sentiment.warning": sentiment.get("warning"),
        "colors.sentiment.danger": sentiment.get("danger"),
    }
    for label, val in fields.items():
        if val is None:
            raise ThemeCompileError(f"tokens missing required field: {label}")
        if not is_valid_hex(val):
            raise ThemeCompileError(f"{label} is not a #RRGGBB hex: {val!r}")
    for c in dc:
        if not is_valid_hex(c):
            raise ThemeCompileError(f"colors.data_colors entry is not a #RRGGBB hex: {c!r}")
    return {
        "colors": {
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "background": colors["background"],
            "text": {
                "primary": text["primary"],
                "secondary": text["secondary"],
                "muted": text["muted"],
            },
            "sentiment": {
                "success": sentiment["success"],
                "warning": sentiment["warning"],
                "danger": sentiment["danger"],
            },
            "data_colors": list(dc),
        }
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py::test_palette_from_tokens_copies_every_color_field -q`
Expected: PASS.

- [ ] **Step 5: Write the failing test for `seed_from_tokens`**

```python
def test_seed_from_tokens_strips_suffix_for_name():
    seed = seed_from_tokens(TOKENS, name_override=None)
    assert seed.name == "executive-dark"          # -design-tokens stripped
    assert seed.mode == "dark"                     # parsed from meta.style "generated (dark)"
    assert seed.accent == "#2FB6C4"


def test_seed_from_tokens_name_override_wins():
    seed = seed_from_tokens(TOKENS, name_override="my-theme")
    assert seed.name == "my-theme"


def test_seed_from_tokens_rejects_bad_slug():
    with pytest.raises(ThemeCompileError):
        seed_from_tokens(TOKENS, name_override="../escape")
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py -k seed_from_tokens -q`
Expected: FAIL — `seed_from_tokens` not defined.

- [ ] **Step 7: Add `_derive_name`, `_mode_from_style`, and `seed_from_tokens`**

Append to `src/seshat/theme_compile.py`:

```python
def _derive_name(tokens_doc: dict) -> str:
    meta = tokens_doc.get("meta") if isinstance(tokens_doc, dict) else None
    raw = meta.get("name") if isinstance(meta, dict) else None
    if not isinstance(raw, str) or not raw:
        raise ThemeCompileError(
            "tokens missing meta.name; pass --name to set the theme basename"
        )
    return raw[: -len(_TOKENS_NAME_SUFFIX)] if raw.endswith(_TOKENS_NAME_SUFFIX) else raw


def _mode_from_style(tokens_doc: dict) -> str:
    """Best-effort read of light/dark from meta.style; defaults to 'light'.

    mode only affects the theme-spec text in theme_gen, never render_theme_json,
    so an imperfect read cannot change the compiled theme.json. Kept simple.
    """
    meta = tokens_doc.get("meta") if isinstance(tokens_doc, dict) else None
    style = meta.get("style", "") if isinstance(meta, dict) else ""
    return "dark" if isinstance(style, str) and "dark" in style.lower() else "light"


def seed_from_tokens(tokens_doc: dict, name_override: str | None) -> ThemeSeed:
    """Build the ThemeSeed render_theme_json needs (it reads seed.name only)."""
    pal = palette_from_tokens(tokens_doc)  # validates colors as a side effect
    c = pal["colors"]
    name = name_override if name_override else _derive_name(tokens_doc)
    _validate_name(name)  # reuse theme_gen's slug guard (may raise ThemeGenError)
    return ThemeSeed(
        name=name,
        mode=_mode_from_style(tokens_doc),
        accent=c["primary"],
        background=c["background"],
        text_primary=c["text"]["primary"],
        text_secondary=c["text"]["secondary"],
        text_muted=c["text"]["muted"],
        data_colors=tuple(c["data_colors"]),
        good=c["sentiment"]["success"],
        neutral=c["sentiment"]["warning"],
        bad=c["sentiment"]["danger"],
    )
```

Note: `_validate_name` raises `theme_gen.ThemeGenError`, not `ThemeCompileError`. Task 3's CLI boundary catches BOTH, so the surfaced error stays clean either way; the module test `test_seed_from_tokens_rejects_bad_slug` uses `pytest.raises(ThemeCompileError)` — so wrap the `_validate_name` call to re-raise as `ThemeCompileError`:

```python
    from .theme_gen import ThemeGenError
    try:
        _validate_name(name)
    except ThemeGenError as exc:
        raise ThemeCompileError(str(exc)) from exc
```

(Place this wrapped call in `seed_from_tokens` in place of the bare `_validate_name(name)` line above.)

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py -k seed_from_tokens -q`
Expected: 3 PASS.

- [ ] **Step 9: Write the failing test for `compile_theme` (round-trip byte-identity — THE core test)**

```python
def _write_tokens(tmp: Path, doc: dict) -> Path:
    p = tmp / "design" / "tokens" / "executive-dark-design-tokens.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return p


def test_compile_is_byte_identical_to_theme_gen(tmp_path: Path):
    # 1. theme-gen produces the reference theme.json for a seed.
    from retail.theme_gen import ThemeSeed, generate

    seed = ThemeSeed(
        name="executive-dark", mode="dark",
        accent="#2FB6C4", background="#12263A",
        text_primary="#F2F6FA", text_secondary="#C4D1DE", text_muted="#93A6B8",
        data_colors=("#A5E3E9", "#7BD6DF", "#52C9D6", "#2FB7C5", "#25919C", "#1C6B73"),
        good="#2E7D5B", neutral="#B5832A", bad="#B23A3A",
    )
    generate(seed, tmp_path, force=True)
    ref_theme = (tmp_path / "themes/executive-dark.theme.json").read_bytes()
    ref_tokens_doc = yaml.safe_load(
        (tmp_path / "design/tokens/executive-dark-design-tokens.yaml").read_text(encoding="utf-8-sig")
    )

    # 2. delete the theme, keep the tokens theme-gen wrote.
    (tmp_path / "themes/executive-dark.theme.json").unlink()

    # 3. compile from those exact committed tokens.
    tokens_path = tmp_path / "design/tokens/executive-dark-design-tokens.yaml"
    out = compile_theme(tokens_path, out_path=None, force=False)

    # 4. byte-identical to theme-gen's output.
    assert out == tmp_path / "themes/executive-dark.theme.json"
    assert out.read_bytes() == ref_theme
    assert ref_tokens_doc  # sanity: tokens were real
```

- [ ] **Step 10: Run the test to verify it fails**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py::test_compile_is_byte_identical_to_theme_gen -q`
Expected: FAIL — `compile_theme` not defined.

- [ ] **Step 11: Add `_resolve_out`, `_load_tokens`, and `compile_theme`**

Append to `src/seshat/theme_compile.py`:

```python
def _load_tokens(tokens_path: Path) -> dict:
    import yaml  # lazy: keep import cost off module load, mirrors DL3

    try:
        with tokens_path.open(encoding="utf-8-sig") as fh:
            doc = yaml.safe_load(fh)
    except OSError as exc:
        raise ThemeCompileError(
            f"tokens file could not be read ({exc.__class__.__name__}): {tokens_path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ThemeCompileError(
            f"tokens file is not valid YAML ({exc.__class__.__name__}): {tokens_path}"
        ) from exc
    if not isinstance(doc, dict):
        raise ThemeCompileError(f"tokens file is not a YAML mapping: {tokens_path}")
    return doc


def _resolve_out(tokens_doc: dict, tokens_path: Path, out_override: Path | None) -> Path:
    """Where to write the theme: --out wins, else meta.compiles_to (repo-relative
    to the tokens file's grandparent, i.e. design/tokens/x.yaml -> repo/themes/x)."""
    if out_override is not None:
        return out_override
    meta = tokens_doc.get("meta")
    compiles_to = meta.get("compiles_to") if isinstance(meta, dict) else None
    if not isinstance(compiles_to, str) or not compiles_to:
        raise ThemeCompileError(
            "tokens have no meta.compiles_to; pass --out to name the theme file"
        )
    # tokens live at <root>/design/tokens/<x>.yaml; compiles_to is repo-relative
    # ("themes/<x>.theme.json"). Resolve against the repo root = parents[2].
    if len(tokens_path.parents) >= 3:
        root = tokens_path.parents[2]
    else:  # a flat/fixture layout: resolve beside the tokens file
        root = tokens_path.parent
    return root / compiles_to


def compile_theme(tokens_path: Path, out_path: Path | None, force: bool) -> Path:
    tokens_doc = _load_tokens(tokens_path)
    seed = seed_from_tokens(tokens_doc, name_override=None)
    palette = palette_from_tokens(tokens_doc)
    check_contrast_or_raise(palette)  # refuse a theme CT1 would reject
    out = _resolve_out(tokens_doc, tokens_path, out_path)
    if out.exists() and not force:
        raise ThemeCompileError(f"{out} exists -- refusing to overwrite (use --force)")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_theme_json(palette, seed), encoding="utf-8", newline="\n")
    return out
```

- [ ] **Step 12: Run the core test to verify it passes**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py::test_compile_is_byte_identical_to_theme_gen -q`
Expected: PASS. (If it fails on bytes, the palette rebuild dropped/reordered a field — compare `render_theme_json` inputs.)

- [ ] **Step 13: Write the remaining module tests (error paths + overwrite guard)**

```python
def test_compile_refuses_overwrite_without_force(tmp_path: Path):
    tokens = _write_tokens(tmp_path, TOKENS)
    compile_theme(tokens, out_path=None, force=False)   # first write ok
    with pytest.raises(ThemeCompileError, match="refusing to overwrite"):
        compile_theme(tokens, out_path=None, force=False)


def test_compile_force_overwrites(tmp_path: Path):
    tokens = _write_tokens(tmp_path, TOKENS)
    compile_theme(tokens, out_path=None, force=False)
    out = compile_theme(tokens, out_path=None, force=True)   # no raise
    assert out.exists()


def test_missing_colors_field_is_clean_error(tmp_path: Path):
    doc = {"meta": TOKENS["meta"], "colors": {**TOKENS["colors"]}}
    del doc["colors"]["background"]
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="colors.background"):
        compile_theme(tokens, out_path=None, force=False)


def test_bad_hex_is_clean_error(tmp_path: Path):
    doc = {"meta": TOKENS["meta"], "colors": {**TOKENS["colors"], "primary": "not-a-hex"}}
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="#RRGGBB"):
        compile_theme(tokens, out_path=None, force=False)


def test_sub_aa_contrast_is_refused(tmp_path: Path):
    # muted text nearly equal to background -> below AA -> refuse.
    doc = {"meta": TOKENS["meta"],
           "colors": {**TOKENS["colors"],
                      "text": {"primary": "#F2F6FA", "secondary": "#C4D1DE", "muted": "#13273B"}}}
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(Exception):  # ThemeGenError from check_contrast_or_raise
        compile_theme(tokens, out_path=None, force=False)


def test_no_compiles_to_and_no_out_is_clean_error(tmp_path: Path):
    doc = {"meta": {"name": "x-design-tokens"}, "colors": TOKENS["colors"]}
    tokens = _write_tokens(tmp_path, doc)
    with pytest.raises(ThemeCompileError, match="compiles_to"):
        compile_theme(tokens, out_path=None, force=False)
```

- [ ] **Step 14: Run the full module test file**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile.py -q`
Expected: all PASS.

- [ ] **Step 15: Commit**

```bash
git add src/seshat/theme_compile.py tests/unit/test_theme_compile.py
git commit -m "feat: theme-compile core -- deterministic tokens->theme (reuses render_theme_json)"
```

---

### Task 2: CLI subcommand `theme-compile`

**Files:**
- Modify: `src/seshat/cli.py` (add subparser near line 205; add dispatch near line 470)
- Create: `tests/unit/test_theme_compile_cli.py`

**Interfaces:**
- Consumes (from Task 1): `compile_theme(tokens_path: Path, out_path: Path | None, force: bool) -> Path`, `ThemeCompileError`.
- Produces: a `theme_compile_main(args) -> int` CLI entry (0 on success, 2 on `ThemeCompileError` or `ThemeGenError`). Add it to `theme_compile.py`.

- [ ] **Step 1: Write the failing CLI test**

```python
# tests/unit/test_theme_compile_cli.py
"""CLI-level test for `retail theme-compile`."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main
from retail.theme_gen import ThemeSeed, generate

pytestmark = pytest.mark.unit

SEED = ThemeSeed(
    name="cli-dark", mode="dark",
    accent="#2FB6C4", background="#12263A",
    text_primary="#F2F6FA", text_secondary="#C4D1DE", text_muted="#93A6B8",
    data_colors=("#A5E3E9", "#7BD6DF", "#52C9D6", "#2FB7C5", "#25919C", "#1C6B73"),
    good="#2E7D5B", neutral="#B5832A", bad="#B23A3A",
)


def test_cli_compiles_and_exits_zero(tmp_path: Path):
    generate(SEED, tmp_path, force=True)
    (tmp_path / "themes/cli-dark.theme.json").unlink()
    tokens = tmp_path / "design/tokens/cli-dark-design-tokens.yaml"
    rc = main(["theme-compile", "--tokens", str(tokens)])
    assert rc == 0
    assert (tmp_path / "themes/cli-dark.theme.json").exists()


def test_cli_missing_tokens_exits_two(tmp_path: Path):
    rc = main(["theme-compile", "--tokens", str(tmp_path / "nope.yaml")])
    assert rc == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile_cli.py -q`
Expected: FAIL — `theme-compile` is not a valid subcommand (argparse `SystemExit: 2` on unknown command, or the dispatch returns non-zero).

- [ ] **Step 3: Add `theme_compile_main` to the module**

Append to `src/seshat/theme_compile.py`:

```python
def theme_compile_main(args) -> int:
    """CLI entry: compile a committed tokens file into its theme.json."""
    out_override = Path(args.out) if getattr(args, "out", None) else None
    try:
        written = compile_theme(
            Path(args.tokens), out_path=out_override, force=args.force
        )
    except ThemeCompileError as exc:
        print(f"theme-compile: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # ThemeGenError from the reused contrast/name guards
        print(f"theme-compile: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    print(
        "reminder: DL3 (fidelity) + DL1 (purity) still gate this theme; "
        "validate in Power BI Desktop. readiness = warning (no pass claimed)."
    )
    return 0
```

Note: the broad `except Exception` is intentional and narrow in effect — the only non-`ThemeCompileError` this path can raise is `theme_gen.ThemeGenError` (from `check_contrast_or_raise`; `_validate_name` is already wrapped in Task 1). Catching it here keeps the CLI from ever emitting a traceback. Do NOT let it swallow programming errors silently — it prints the message.

- [ ] **Step 4: Add the subparser in `cli.py`**

In `src/seshat/cli.py`, immediately after the `theme-gen` parser block (after line 204, the `themegen.add_argument("--force", ...)` call), add:

```python
    # Tokens -> theme compile (deterministic; reuses theme-gen's renderer). Reads a
    # committed design-tokens YAML and writes its matching theme.json. The generator
    # whose output DL3 checks; removes the hand-edit that desyncs a theme from tokens.
    themecompile = sub.add_parser(
        "theme-compile",
        help="compile a committed design-tokens YAML into its theme.json",
    )
    themecompile.add_argument(
        "--tokens", required=True, metavar="PATH",
        help="the *-design-tokens.yaml file to compile",
    )
    themecompile.add_argument(
        "--out", default=None, metavar="PATH",
        help="theme.json output path (default: the tokens' meta.compiles_to)",
    )
    themecompile.add_argument(
        "--force", action="store_true", help="overwrite an existing theme.json"
    )
```

- [ ] **Step 5: Add the dispatch branch in `cli.py`**

In `src/seshat/cli.py`, immediately after the `theme-gen` dispatch block (after the `return theme_gen_main(args)` at ~line 473), add:

```python
    if args.command == "theme-compile":
        from .theme_compile import theme_compile_main

        return theme_compile_main(args)
```

- [ ] **Step 6: Run the CLI test to verify it passes**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_theme_compile_cli.py -q`
Expected: 2 PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/cli.py src/seshat/theme_compile.py tests/unit/test_theme_compile_cli.py
git commit -m "feat: wire theme-compile CLI subcommand"
```

---

### Task 3: End-to-end verification against the live committed tokens + full gate

**Files:**
- No new files (verification-only task; folds in the doc line for `themes/README.md` if warranted).

**Interfaces:**
- Consumes: the shipped `theme-compile` verb; the live `design/tokens/executive-dark-design-tokens.yaml` + `tower-retail-design-tokens.yaml`.

- [ ] **Step 1: Confirm compile reproduces the committed live theme byte-for-byte**

Run:
```bash
cd C:/Users/user/Documents/GitHub/Seshat_BI
cp themes/executive-dark.theme.json /tmp/ed-ref.json
PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['theme-compile','--tokens','design/tokens/executive-dark-design-tokens.yaml','--force']))"
diff themes/executive-dark.theme.json /tmp/ed-ref.json && echo "BYTE-IDENTICAL"
```
Expected: `wrote themes/executive-dark.theme.json` + `BYTE-IDENTICAL`, no diff. (If diff is non-empty, the live theme predates a token edit — that is a real DL3-relevant finding; STOP and report it rather than committing the regenerated theme.)

- [ ] **Step 2: Restore the reference (compile must leave the tree clean)**

Run:
```bash
cd C:/Users/user/Documents/GitHub/Seshat_BI && git checkout themes/executive-dark.theme.json && git status --short
```
Expected: no modification to `themes/executive-dark.theme.json` remains staged/unstaged (the compile was a proof, not a change).

- [ ] **Step 3: Run the full gate the CI enforces**

Run:
```bash
cd C:/Users/user/Documents/GitHub/Seshat_BI
ruff format --check src tests && ruff check src tests && PYTHONPATH=src python -m pytest -m unit -q && PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['check']))"
```
Expected: format clean, lint clean, all unit tests PASS, `retail check` → `Passed` (exit 0). DL3 passes on the existing committed pairs (unchanged), confirming the compile-checker relationship end to end.

- [ ] **Step 4: Add a one-line note to `themes/README.md`**

Add under the existing theme-list section (match the file's existing bullet style):

```markdown
- Regenerate a theme from its committed tokens without hand-editing:
  `retail theme-compile --tokens design/tokens/<name>-design-tokens.yaml`
  (deterministic; DL3 verifies the result matches the tokens).
```

- [ ] **Step 5: Commit**

```bash
git add themes/README.md
git commit -m "docs: note theme-compile in themes/README"
```

- [ ] **Step 6: Push and open the PR**

```bash
cd C:/Users/user/Documents/GitHub/Seshat_BI
git push -u origin feat/theme-compile-from-tokens
gh pr create --title "feat: theme-compile -- deterministic tokens->theme verb" --body "$(cat <<'BODY'
Adds `retail theme-compile`: reads a committed design-tokens YAML and writes its
matching `theme.json`, reusing `theme_gen.render_theme_json` so the output is
byte-identical to what `theme-gen` produced. The generator whose output DL3
(token->theme fidelity) already checks; removes the hand-edit that is otherwise the
only way to desync a theme from its tokens.

DEFINE-only: writes one `themes/*.theme.json`. No PBIR, no ADR, no new rule, no
color decision (every value copied from committed tokens). See
`docs/superpowers/specs/2026-07-06-theme-compile-from-tokens-design.md`.

## Test plan
- [x] round-trip byte-identity: theme-gen -> delete -> theme-compile == original
- [x] palette rebuilt field-for-field from committed tokens
- [x] error paths (missing field, bad hex, no target, sub-AA contrast) -> clean exit 2
- [x] overwrite refused without --force
- [x] compile reproduces live executive-dark theme byte-for-byte
- [x] ruff format/check + pytest -m unit + retail check all green
BODY
)"
```

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- Circular-framing / reframe → captured in plan header + module docstring (Task 1 Step 3). ✓
- Reuse `render_theme_json` / no re-derivation → Task 1 Step 11 (`compile_theme` delegates). ✓
- Palette rebuilt from committed values → Task 1 Steps 3, 7. ✓
- DL3 relationship (generator it checks) → docstring + Task 3 Step 3 (DL3 passes). ✓
- Error handling (missing/unreadable/bad-hex/no-target/sub-AA/overwrite) → Task 1 Steps 11, 13; Task 2 Step 3. ✓
- `meta.compiles_to` as default target → Task 1 `_resolve_out`. ✓
- Not-latent claim (runs on live tokens today) → Task 3 Step 1. ✓
- Round-trip byte-identity core test → Task 1 Step 9. ✓
- No self-granted pass / no score → `theme_compile_main` reminder text (Task 2 Step 3). ✓

**2. Placeholder scan** — no TBD/TODO; every code step shows full code; every run step shows the exact command + expected output. The one `except Exception` is explained and justified, not vague. ✓

**3. Type consistency** — `compile_theme(tokens_path, out_path, force) -> Path` is consumed identically by `theme_compile_main` and both test files. `palette_from_tokens`/`seed_from_tokens` signatures match their call sites. `ThemeCompileError` is the raised type in every module test; `_validate_name`'s `ThemeGenError` is explicitly re-wrapped (Task 1 Step 7 note) so `test_seed_from_tokens_rejects_bad_slug`'s `pytest.raises(ThemeCompileError)` holds. ✓

**Dead-code check:** the module uses explicit `.get()` + None-checks throughout; no unused helper is introduced. ✓
