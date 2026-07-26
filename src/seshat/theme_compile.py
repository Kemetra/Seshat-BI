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
from .theme_style_cards import CHROME_TOKEN_KEYS, PAGE_TOKEN_KEYS, StyleCardError


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


def _prune_generator_cards(
    style: object, owned: tuple[str, ...], rendered_cards: dict[str, frozenset[str]]
) -> object:
    """One style-preset dict with the generator-written PROPERTIES removed.

    Pruning is property-level, not card-level (#520). The generator writes
    individual properties into a card, so removing the whole card would strip a
    human's hand-tune sitting beside them -- from BOTH sides of the deferred
    comparison, which registers no conflict and lets ``--force`` overwrite it
    silently. A card is emptied (and dropped) only when every property in it
    was generator-written.
    """
    if not isinstance(style, dict):
        return style
    kept: dict[str, object] = {}
    for card, value in style.items():
        if card not in owned:
            kept[card] = value
            continue
        remainder = _human_owned_card(value, rendered_cards.get(card, frozenset()))
        if remainder:
            kept[card] = remainder
    return kept


def _card_properties(card: object) -> frozenset[str]:
    """Property names inside a theme-JSON card.

    A card is a LIST of property bags -- ``[{prop: value, ...}]`` -- per the
    published schema (``visualStyles > visual > preset > card > [{...}]``), not
    a bare mapping. Reading it as a mapping yields list indices, so the shape is
    handled in one place rather than at each call site.
    """
    if not isinstance(card, list):
        return frozenset()
    names: set[str] = set()
    for entry in card:
        if isinstance(entry, dict):
            names.update(entry)
    return frozenset(names)


def _human_owned_card(card: object, rendered_props: frozenset[str]) -> object:
    """One card's property bags minus the properties the renderer emitted.

    Returns a card in the same ``[{...}]`` shape carrying only the leftover
    human properties, or ``None`` when nothing is left. A card that is not a
    list cannot be compared property-wise, so it survives whole rather than
    being silently dropped.
    """
    if not isinstance(card, list):
        return card
    kept_entries: list[dict] = []
    for entry in card:
        if not isinstance(entry, dict):
            kept_entries.append(entry)
            continue
        remainder = {k: v for k, v in entry.items() if k not in rendered_props}
        if remainder:
            kept_entries.append(remainder)
    return kept_entries or None


def _rendered_star_cards(
    rendered: object, visual_type: str
) -> dict[str, frozenset[str]]:
    """Card name -> property names the RENDERED theme emits for ``visual_type``'s
    ``"*"`` preset.

    Emission is conditional on the tokens (a tokens file with no ``chrome:``
    or ``page:`` group emits none of these cards at all), so a card must only
    be treated as generator-owned when the rendered document proves the
    generator actually wrote it -- never from the static
    ``_GENERATOR_OWNED_CARDS`` table alone (finding 1 / P1).

    Carrying the PROPERTY names, not just the card names, is what lets pruning
    match the generator's real write granularity (#520).
    """
    if not isinstance(rendered, dict):
        return {}
    presets = rendered.get(visual_type)
    star = presets.get("*") if isinstance(presets, dict) else None
    if not isinstance(star, dict):
        return {}
    return {card: _card_properties(value) for card, value in star.items()}


def _human_owned_presets(
    presets: dict, owned: tuple[str, ...], rendered_cards: dict[str, frozenset[str]]
) -> dict[str, object]:
    """One visual type's style presets with generator-written properties pruned.

    A NAMED style preset (anything but ``"*"``) is human-authored by definition
    and survives verbatim; the ``"*"`` preset is pruned of the cards that are
    BOTH declared owned (``owned``) AND actually emitted by the rendered theme
    (``rendered_cards``) -- a card absent from the rendered document is
    human-owned regardless of the static table, and dropped entirely if that
    empties it, so it cannot register as a spurious conflict.

    Within an emitted card the pruning is per-PROPERTY (#520), so a human
    property beside a generated one survives and stays visible to the guard.
    """
    effective_owned = tuple(c for c in owned if c in rendered_cards)
    kept_presets: dict[str, object] = {}
    for preset_name, style in presets.items():
        if preset_name != "*":
            kept_presets[preset_name] = style
            continue
        pruned = _prune_generator_cards(style, effective_owned, rendered_cards)
        if pruned:
            kept_presets[preset_name] = pruned
    return kept_presets


def _human_owned_visual_styles(vs: object, rendered: object) -> object:
    """``vs`` with every card the RENDERED theme actually emits removed.

    Table-driven over ``_GENERATOR_OWNED_CARDS`` so a new emission target (a new
    visual type or card) is declared in one place, but a card is only pruned
    when ``rendered`` proves the generator actually wrote it there (finding 1):
    emission is conditional on the tokens, so an older tokens file with no
    ``chrome:``/``page:`` group must not have its hand-tuned cards pruned from
    both sides of the comparison and silently deleted. Comparing the returned
    value across existing-vs-rendered detects a hand-tuned visualStyle a human
    added while ignoring token-driven churn the generator legitimately owns.
    An empty style preset or visual type is dropped entirely so it cannot
    register as a spurious conflict.
    """
    if not isinstance(vs, dict):
        return vs
    result: dict[str, object] = {}
    for visual_type, presets in vs.items():
        owned = _GENERATOR_OWNED_CARDS.get(visual_type)
        if owned is None or not isinstance(presets, dict):
            result[visual_type] = presets
            continue
        rendered_cards = _rendered_star_cards(rendered, visual_type)
        kept_presets = _human_owned_presets(presets, owned, rendered_cards)
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
# CHROME_TOKEN_KEYS/PAGE_TOKEN_KEYS (imported from theme_style_cards, the single
# source both this reader and theme_gen's writer share) are a plain allow-list
# copy: an ABSENT group returns None (not {}), so a tokens file predating
# chrome/page is byte-identical to before (no chrome=/page= divergence from
# the ThemeSeed default).


def _group_from_tokens(
    tokens_doc: dict, group: str, keys: tuple[str, ...]
) -> dict | None:
    """A shallow copy of tokens_doc[group] restricted to ``keys``, or None.

    None (not {}) when the group is absent or empty, so seed_from_tokens
    passes None through to ThemeSeed.chrome/page unchanged -- the exact
    default that keeps every pre-existing tokens file's compiled output
    byte-identical (chrome=None/page=None emit no section-5/6/7 card at all;
    see render_theme_json).

    A PRESENT-but-mistyped group (e.g. ``chrome: []`` or ``page: "dark"``) is
    a different case entirely and must not collapse into the same None: that
    would compile successfully while silently dropping every requested
    section 5/6/7 card, with theme_style_cards' own validators never seeing
    the value (finding B). Only a genuinely ABSENT key skips the type check;
    once the key is present, its value must be a mapping (empty is fine --
    it is a no-op group, not a type error).

    An UNKNOWN key inside the group is rejected rather than filtered away
    (#521). Silently dropping ``chrome.data_label`` or
    ``page.wallpaper_transparancy`` makes a typo indistinguishable from an
    intentionally absent setting: compilation succeeds, the requested styling
    never appears, and nothing says why. The vocabulary is closed and small, so
    naming the offender and the accepted keys is strictly better than guessing.
    """
    if group not in tokens_doc:
        return None
    block = _require_group_mapping(tokens_doc[group], group)
    if not block:
        return None
    _reject_unknown_keys(block, group, keys)
    return {k: block[k] for k in keys if k in block}


def _require_group_mapping(block: object, group: str) -> dict:
    """``block`` as a mapping, or raise naming the group and the wrong type."""
    if not isinstance(block, dict):
        raise ThemeCompileError(
            f"tokens {group!r} must be a mapping, got {type(block).__name__}"
        )
    return block


def _reject_unknown_keys(block: dict, group: str, keys: tuple[str, ...]) -> None:
    """Refuse any key outside the group's closed vocabulary (#521)."""
    unknown = sorted(k for k in block if k not in keys)
    if unknown:
        raise ThemeCompileError(
            f"tokens {group!r} has unknown key(s) {', '.join(map(repr, unknown))}; "
            f"accepted keys are {', '.join(keys)}"
        )


def chrome_from_tokens(tokens_doc: dict) -> dict | None:
    """The optional ``chrome:`` token group (theme-spec section 5), or None."""
    return _group_from_tokens(tokens_doc, "chrome", CHROME_TOKEN_KEYS)


def page_from_tokens(tokens_doc: dict) -> dict | None:
    """The optional ``page:`` token group (theme-spec sections 6+7), or None."""
    return _group_from_tokens(tokens_doc, "page", PAGE_TOKEN_KEYS)


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
            # churn under the generator-owned *//* keys is not a hand-tuned
            # conflict. Both sides prune against the SAME rendered document
            # (rendered_val): every card in rendered_val is trivially "in
            # rendered_val", so the rendered side prunes to exactly what the
            # generator emits, while the existing side only loses a card if
            # the generator actually wrote it there too (finding 1).
            existing_val = _human_owned_visual_styles(existing_val, rendered_val)
            rendered_val = _human_owned_visual_styles(rendered_val, rendered_val)
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
