"""Tokens -> theme compiler (DEFINE-only).

Reconstructs a Power BI ``theme.json`` from a *committed* design-tokens YAML by
rebuilding the palette from the tokens' own values and delegating to the existing
``theme_gen.render_theme_json`` -- the single source of the theme's JSON shape.
It chooses no color, derives nothing, and invents no key: every value written is
copied from the tokens. The output is byte-identical to what ``theme-gen`` wrote
for those tokens ONLY when the theme was generated and never hand-tuned; that is
the invariant DL3 (token->theme fidelity) asserts for a fresh theme. Once a theme
has been hand-tuned, compile repairs DL3-GOVERNED drift (dataColors, background)
but REFUSES to overwrite DL3-DEFERRED, human-owned fields (name, foreground,
tableAccent, good/neutral/bad, visualStyles) even with --force -- it reports the
conflicting fields for manual reconciliation rather than silently overriding a
human decision (Principle V).

DEFINE-only: writes one ``themes/*.theme.json``; no PBIR/visual.json/model, no
pbi-cli / live Power BI / network. Reuses ``theme_gen``'s renderer, contrast gate,
and name-slug guard; ``seshat.color`` for hex validation. Never self-grants a
readiness pass and emits no score (rule #9 / Principle V).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .color import is_valid_hex
from .theme_gen import (
    MIN_LABEL_FONT_PT,
    MIN_TITLE_FONT_PT,
    ThemeGenError,
    ThemeSeed,
    _validate_name,
    _validate_transparency,
    check_composite_contrast_or_raise,
    check_contrast_or_raise,
    check_font_floor_or_raise,
    check_non_text_contrast_or_raise,
    render_theme_json,
)
from .theme_style_cards import StyleCardError


class ThemeCompileError(Exception):
    """A compile input/output problem surfaced cleanly (never a traceback)."""


_TOKENS_NAME_SUFFIX = "-design-tokens"

# render_theme_json's output shape has two disjoint field groups:
#   - DL3-GOVERNED (dataColors, background): DL3 already reconciles these, so
#     compile legitimately repairs drift here -- safe to overwrite.
#   - DL3-DEFERRED (this tuple): DL3 does NOT check these; a committed theme
#     may be hand-tuned here under a named-owner ruling (e.g. tower-seshat.
#     theme.json, commit 947e4fa). Silently overwriting them would destroy a
#     human judgment call, so compile must refuse rather than repair.
_DL3_DEFERRED_FIELDS = (
    "name",
    "foreground",
    "tableAccent",
    "good",
    "neutral",
    "bad",
    "visualStyles",
)

# Generator-owned cards per visual type. A card listed here is written by
# theme_gen from committed tokens, so it is NEVER a human hand-tune -- pruning it
# before the DL3-deferred comparison is what lets a token change recompile over an
# existing theme (T8/T18, and spec 5/6/7). Any card NOT listed is human-owned.
_GENERATOR_OWNED_CARDS: dict[str, tuple[str, ...]] = {
    "*": ("title", "labels", "background", "categoryAxis", "valueAxis", "border"),
    "page": ("background", "outspace", "outspacePane", "filterCard"),
}

# Back-compat alias: the original name, now derived from the table above.
_GENERATOR_OWNED_VISUAL_STYLE_KEYS = _GENERATOR_OWNED_CARDS["*"]


def _prune_generator_cards(style: object, owned: tuple[str, ...]) -> object:
    """One style-preset dict with the generator-owned cards removed."""
    if not isinstance(style, dict):
        return style
    return {k: v for k, v in style.items() if k not in owned}


def _human_owned_presets(presets: dict, owned: tuple[str, ...]) -> dict[str, object]:
    """One visual type's style presets with generator-owned cards pruned.

    A NAMED style preset (anything but ``"*"``) is human-authored by definition
    and survives verbatim; the ``"*"`` preset is pruned of ``owned`` cards and
    dropped entirely if that empties it, so it cannot register as a spurious
    conflict.
    """
    kept_presets: dict[str, object] = {}
    for preset_name, style in presets.items():
        if preset_name != "*":
            kept_presets[preset_name] = style
            continue
        pruned = _prune_generator_cards(style, owned)
        if pruned:
            kept_presets[preset_name] = pruned
    return kept_presets


def _human_owned_visual_styles(vs: object) -> object:
    """``visualStyles`` with every generator-owned card removed.

    Table-driven over ``_GENERATOR_OWNED_CARDS`` so a new emission target (a new
    visual type or card) is declared in one place. Comparing the returned value
    across existing-vs-rendered detects a hand-tuned visualStyle a human added
    while ignoring token-driven churn the generator legitimately owns. An empty
    style preset or visual type is dropped entirely so it cannot register as a
    spurious conflict.
    """
    if not isinstance(vs, dict):
        return vs
    result: dict[str, object] = {}
    for visual_type, presets in vs.items():
        owned = _GENERATOR_OWNED_CARDS.get(visual_type)
        if owned is None or not isinstance(presets, dict):
            result[visual_type] = presets
            continue
        kept_presets = _human_owned_presets(presets, owned)
        if kept_presets:
            result[visual_type] = kept_presets
    return result


def _require_mapping(value: object, label: str) -> dict:
    """Return ``value`` as a dict, or raise naming the missing/mistyped field."""
    if not isinstance(value, dict):
        raise ThemeCompileError(f"tokens missing required field: {label}")
    return value


def _require_hex(value: object, label: str) -> str:
    """Return ``value`` as a validated #RRGGBB hex, or raise naming the field."""
    if value is None:
        raise ThemeCompileError(f"tokens missing required field: {label}")
    if not is_valid_hex(value):
        raise ThemeCompileError(f"{label} is not a #RRGGBB hex: {value!r}")
    return value


def _require_data_colors(colors: dict) -> list[str]:
    """Return a validated non-empty list of #RRGGBB data colors, or raise."""
    dc = colors.get("data_colors")
    if not isinstance(dc, list) or not dc:
        raise ThemeCompileError("tokens missing a non-empty colors.data_colors list")
    for c in dc:
        if not is_valid_hex(c):
            raise ThemeCompileError(
                f"colors.data_colors entry is not a #RRGGBB hex: {c!r}"
            )
    return list(dc)


def palette_from_tokens(tokens_doc: dict) -> dict:
    """Rebuild build_palette's output shape purely from committed token values."""
    colors = _require_mapping(
        _require_mapping(tokens_doc, "root").get("colors"), "colors"
    )
    text = _require_mapping(colors.get("text"), "colors.text")
    sentiment = _require_mapping(colors.get("sentiment"), "colors.sentiment")
    pal: dict = {
        "colors": {
            "primary": _require_hex(colors.get("primary"), "colors.primary"),
            "secondary": _require_hex(colors.get("secondary"), "colors.secondary"),
            "background": _require_hex(colors.get("background"), "colors.background"),
            "text": {
                "primary": _require_hex(text.get("primary"), "colors.text.primary"),
                "secondary": _require_hex(
                    text.get("secondary"), "colors.text.secondary"
                ),
                "muted": _require_hex(text.get("muted"), "colors.text.muted"),
            },
            "sentiment": {
                "success": _require_hex(
                    sentiment.get("success"), "colors.sentiment.success"
                ),
                "warning": _require_hex(
                    sentiment.get("warning"), "colors.sentiment.warning"
                ),
                "danger": _require_hex(
                    sentiment.get("danger"), "colors.sentiment.danger"
                ),
            },
            "data_colors": _require_data_colors(colors),
        }
    }
    try:
        transparency = _validate_transparency(tokens_doc.get("transparency"))
    except ThemeGenError as exc:
        raise ThemeCompileError(str(exc)) from exc
    if transparency is not None:
        pal["transparency"] = transparency
    return pal


# Optional top-level token groups that feed theme-spec sections 5 (chrome) and
# 6+7 (page). Read verbatim, no derivation/defaulting -- validation is entirely
# theme_style_cards' job (build_star_cards / build_page_cards), so a bad value
# here is deferred to render time and caught at the compile boundary below.
# Keys are a plain allow-list copy: an ABSENT group returns None (not {}), so a
# tokens file predating chrome/page is byte-identical to before (no chrome=/
# page= divergence from the ThemeSeed default).
_CHROME_KEYS = (
    "gridline",
    "border",
    "title_align",
    "data_labels",
    "number_format",
)
_PAGE_KEYS = (
    "background",
    "background_transparency",
    "wallpaper",
    "wallpaper_transparency",
    "filter_pane_background",
    "filter_pane_text",
    "filter_card_applied",
    "filter_card_available",
)


def _group_from_tokens(
    tokens_doc: dict, group: str, keys: tuple[str, ...]
) -> dict | None:
    """A shallow copy of tokens_doc[group] restricted to ``keys``, or None.

    None (not {}) when the group is absent or empty, so seed_from_tokens
    passes None through to ThemeSeed.chrome/page unchanged -- the exact
    default that keeps every pre-existing tokens file's compiled output
    byte-identical (chrome=None/page=None emit no section-5/6/7 card at all;
    see render_theme_json).
    """
    block = tokens_doc.get(group)
    if not isinstance(block, dict) or not block:
        return None
    return {k: block[k] for k in keys if k in block}


def chrome_from_tokens(tokens_doc: dict) -> dict | None:
    """The optional ``chrome:`` token group (theme-spec section 5), or None."""
    return _group_from_tokens(tokens_doc, "chrome", _CHROME_KEYS)


def page_from_tokens(tokens_doc: dict) -> dict | None:
    """The optional ``page:`` token group (theme-spec sections 6+7), or None."""
    return _group_from_tokens(tokens_doc, "page", _PAGE_KEYS)


def _derive_name(tokens_doc: dict) -> str:
    meta = tokens_doc.get("meta") if isinstance(tokens_doc, dict) else None
    raw = meta.get("name") if isinstance(meta, dict) else None
    if not isinstance(raw, str) or not raw:
        raise ThemeCompileError(
            "tokens missing meta.name; meta.name is required to derive the "
            "theme basename"
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
    # Per-KEY fallback, not per-block: a pre-feature tokens file may have no
    # typography block at all (executive-dark), or a typography block that
    # predates these two keys (tower-retail's base_size_pt/scale_pt block).
    # Either way, a missing KEY falls back to the fixed constant -- never to
    # a guessed/inherited value -- so a byte-identical recompile of an
    # unmodified tokens file never trips a phantom font-field conflict.
    typo = tokens_doc.get("typography") or {}
    title_font_pt = float(typo.get("title_font_pt", MIN_TITLE_FONT_PT))
    label_font_pt = float(typo.get("label_font_pt", MIN_LABEL_FONT_PT))
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
        title_font_pt=title_font_pt,
        label_font_pt=label_font_pt,
        transparency=pal.get("transparency"),
        chrome=chrome_from_tokens(tokens_doc),
        page=page_from_tokens(tokens_doc),
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


def _deferred_field_conflicts(existing: dict, rendered: dict) -> list[str]:
    """Names of DL3-deferred fields where ``existing`` and ``rendered`` disagree.

    Deferred fields are human-owned (DL3 never reconciles them); comparing
    decoded JSON values (not raw file text) means CRLF/whitespace differences
    in the committed file can never register as a conflict.
    """
    conflicts = []
    for field in _DL3_DEFERRED_FIELDS:
        existing_val = existing.get(field)
        rendered_val = rendered.get(field)
        if field == "visualStyles":
            # Compare only the human-owned remainder -- token-driven font/overlay
            # churn under the generator-owned *//* keys is not a hand-tuned conflict.
            existing_val = _human_owned_visual_styles(existing_val)
            rendered_val = _human_owned_visual_styles(rendered_val)
        if existing_val != rendered_val:
            conflicts.append(field)
    return conflicts


def _load_existing_theme(out: Path) -> dict:
    try:
        with out.open(encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except OSError as exc:
        raise ThemeCompileError(
            f"existing theme file could not be read ({exc.__class__.__name__}): {out}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ThemeCompileError(
            f"existing theme file is not valid JSON ({exc.__class__.__name__}): {out}"
        ) from exc
    if not isinstance(doc, dict):
        raise ThemeCompileError(f"existing theme file is not a JSON object: {out}")
    return doc


def compile_theme(tokens_path: Path, out_path: Path | None, force: bool) -> Path:
    tokens_doc = _load_tokens(tokens_path)
    seed = seed_from_tokens(tokens_doc, name_override=None)
    palette = palette_from_tokens(tokens_doc)
    check_contrast_or_raise(palette)  # refuse a theme CT1 would reject
    try:
        check_font_floor_or_raise(seed)  # refuse a committed sub-floor font
        check_composite_contrast_or_raise(palette)  # refuse a failing overlay
        # WCAG 3:1 non-text floor (gridline/border vs background) -- the same
        # gate theme-gen runs before writing, now also enforced on a committed
        # tokens file that declares an invisible gridline/border (finding 4).
        check_non_text_contrast_or_raise(palette, seed)
    except ThemeGenError as exc:
        raise ThemeCompileError(str(exc)) from exc
    out = _resolve_out(tokens_doc, tokens_path, out_path)
    try:
        # render_theme_json calls into theme_style_cards (build_star_cards /
        # build_page_cards) for the seed's chrome/page groups; a bad token
        # there raises StyleCardError, which must surface as a clean
        # ThemeCompileError at this boundary -- never a raw traceback.
        rendered_str = render_theme_json(palette, seed)
    except StyleCardError as exc:
        raise ThemeCompileError(str(exc)) from exc
    if out.exists():
        existing = _load_existing_theme(out)
        conflicts = _deferred_field_conflicts(existing, json.loads(rendered_str))
        if conflicts:
            # Runs even when force=True: force overwrites DL3-governed drift,
            # it must never bypass a human-owned/DL3-deferred field conflict.
            names = ", ".join(sorted(conflicts))
            raise ThemeCompileError(
                f"{out} has hand-tuned DL3-deferred field(s) that differ from "
                f"the compiled tokens: {names}. These fields are human-owned "
                "(DL3 does not check them) and compile will not silently "
                "overwrite them -- reconcile the discrepancy by hand."
            )
        if not force:
            raise ThemeCompileError(
                f"{out} exists -- refusing to overwrite (use --force)"
            )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered_str, encoding="utf-8", newline="\n")
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
