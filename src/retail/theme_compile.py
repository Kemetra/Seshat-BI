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
    ThemeGenError,
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
        raise ThemeCompileError("tokens missing a non-empty colors.data_colors list")
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
            raise ThemeCompileError(
                f"colors.data_colors entry is not a #RRGGBB hex: {c!r}"
            )
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


def _derive_name(tokens_doc: dict) -> str:
    meta = tokens_doc.get("meta") if isinstance(tokens_doc, dict) else None
    raw = meta.get("name") if isinstance(meta, dict) else None
    if not isinstance(raw, str) or not raw:
        raise ThemeCompileError(
            "tokens missing meta.name; pass --name to set the theme basename"
        )
    return (
        raw[: -len(_TOKENS_NAME_SUFFIX)] if raw.endswith(_TOKENS_NAME_SUFFIX) else raw
    )


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
    try:
        _validate_name(name)  # reuse theme_gen's slug guard
    except ThemeGenError as exc:
        raise ThemeCompileError(str(exc)) from exc
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


def _resolve_out(
    tokens_doc: dict, tokens_path: Path, out_override: Path | None
) -> Path:
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
