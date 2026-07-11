"""Design-lint rule DL3: token->theme fidelity reconciler (surface 3).

The FIDELITY sibling of DL1 (purity). DL1 asserts a committed theme carries no
forbidden business-logic KEYS; DL3 asserts the styling VALUES a theme carries
equal the values the design tokens declare compile into it. Together they close
the surface-3 loop: the theme is clean AND faithful to its token source.

DECLARED-CORRESPONDENCE ONLY (Principle V). DL3 reconciles exactly the two
correspondences a human has already committed in the tokens source; it never
invents a mapping a human owns:

  * ``colors.data_colors[i]`` == theme ``dataColors[i]`` -- positional, declared
    by the tokens comment "theme dataColors compiles from THIS list" (T029).
  * ``colors.background`` == theme ``background`` -- identity-named.

DELIBERATELY OUT OF SCOPE for DL3 (a human ruling gates them, not this rule):
  * sentiment fidelity (tokens ``success``/``warning``/``danger`` vs theme
    ``good``/``neutral``/``bad``). The theme's middle slot is an amber that
    matches tokens ``warning`` BY COLOR but tokens ``neutral`` BY NAME -- a 4->3
    correspondence that is a genuine Principle-V ambiguity. DL3 never picks it.
    The follow-on rule DL8 (below) carries it once a human freezes the map: DL8
    reads an opt-in ``meta.sentiment_map`` a human has committed and FLAGS any
    drift, staying provably inert (no finding, ever) until that map exists.
  * ``text.primary`` -> theme ``foreground`` (same: no committed correspondence).

The pairing is generic: DL3 finds the tokens file by its ``meta.compiles_to``
field (the tokens declare their own theme target) and reconciles that pair. No
tenant/example/brand literal appears here (Principle VII); the field names
(``dataColors``, ``background``) are generic Power BI theme keys.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL3"

# Generic discovery suffixes (never an enumerated tenant list -- Principle VII).
_TOKENS_SUFFIX = "-design-tokens.yaml"
_THEME_SUFFIX = ".theme.json"

# For the fixture tests the pair lives as bare ``tokens.yaml`` / ``theme.json``;
# the live pair uses the descriptive suffixes above. Accept either token-file
# basename generically.
_TOKENS_BASENAMES = ("tokens.yaml",)


def _iter_tokens_files(ctx: RuleContext) -> list[str]:
    """Committed design-tokens files, generic discovery, fixtures exempted."""
    out = []
    for p in ctx.tracked_files:
        if is_test_path(p):
            continue
        base = p.rsplit("/", 1)[-1]
        if p.endswith(_TOKENS_SUFFIX) or base in _TOKENS_BASENAMES:
            out.append(p)
    return out


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    try:
        with path.open(encoding="utf-8-sig") as fh:
            return yaml.safe_load(fh), None
    except (OSError, yaml.YAMLError) as exc:
        return None, exc.__class__.__name__


def _load_json(path: Path) -> tuple[Any, str | None]:
    try:
        with path.open(encoding="utf-8-sig") as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, exc.__class__.__name__


def _declared_compiles_to(tokens_doc: Any) -> str | None:
    """The tokens' own ``meta.compiles_to`` target string, or None if absent."""
    if not isinstance(tokens_doc, dict):
        return None
    meta = tokens_doc.get("meta")
    if not isinstance(meta, dict):
        return None
    compiles_to = meta.get("compiles_to")
    return compiles_to if isinstance(compiles_to, str) and compiles_to else None


def _resolve_compiles_to(compiles_to: str, tokens_rel: str, ctx: RuleContext) -> str:
    """Pick the on-disk path for a declared ``compiles_to``.

    A compiles_to may be repo-relative (live) or dir-relative (fixture): prefer
    whichever candidate exists, else fall back to the raw value as declared.
    """
    parent = tokens_rel.rsplit("/", 1)[0] if "/" in tokens_rel else ""
    candidates = [compiles_to]
    if parent:
        candidates.append(f"{parent}/{compiles_to}")
    for cand in candidates:
        if (ctx.repo_root / cand).exists():
            return cand
    return compiles_to


def _sole_committed_theme(ctx: RuleContext) -> str | None:
    """The single committed ``*.theme.json`` (fixtures exempted), or None when
    there is not exactly one to pair unambiguously."""
    themes = [
        p
        for p in ctx.tracked_files
        if p.endswith(_THEME_SUFFIX) and not is_test_path(p)
    ]
    return themes[0] if len(themes) == 1 else None


def _theme_rel_for(tokens_rel: str, tokens_doc: Any, ctx: RuleContext) -> str | None:
    """Resolve the theme file this tokens file compiles to.

    Prefers the tokens' own ``meta.compiles_to`` (a human-declared target,
    resolved relative to the tokens file's directory). Falls back to a single
    committed ``*.theme.json`` when compiles_to is absent.
    """
    compiles_to = _declared_compiles_to(tokens_doc)
    if compiles_to is not None:
        return _resolve_compiles_to(compiles_to, tokens_rel, ctx)
    return _sole_committed_theme(ctx)


def _background_findings(
    colors: dict, theme: dict, theme_rel: str
) -> Iterable[Finding]:
    """Reconcile the identity-named ``background`` correspondence, if both sides
    declare it -- a missing value on either side is out of scope, not drift."""
    tok_bg = colors.get("background")
    thm_bg = theme.get("background")
    if tok_bg is None or thm_bg is None:
        return
    if tok_bg == thm_bg:
        return
    yield Finding(
        RULE_ID,
        Severity.ERROR,
        f"theme background {thm_bg!r} does not match the token "
        f"declared value {tok_bg!r}",
        f"{theme_rel}#/background",
    )


def _data_colors_findings(
    colors: dict, theme: dict, theme_rel: str
) -> Iterable[Finding]:
    """Reconcile the positional, T029-declared ``data_colors`` correspondence."""
    tok_dc = colors.get("data_colors")
    thm_dc = theme.get("dataColors")
    if not isinstance(tok_dc, list):
        return  # tokens declare no palette -- nothing to reconcile
    if not isinstance(thm_dc, list):
        # The tokens DECLARE data_colors compiles into the theme (T029); a theme
        # that drops dataColors (or gives it a non-list type) has no categorical
        # palette to reconcile -- a fidelity failure, not a silent pass.
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"tokens declare {len(tok_dc)} data_colors but the theme has no "
            f"dataColors list (missing or not a list); the compiled palette is "
            f"absent and fidelity cannot be reconciled",
            f"{theme_rel}#/dataColors",
        )
        return
    if len(tok_dc) != len(thm_dc):
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"data_colors length {len(tok_dc)} does not match theme "
            f"dataColors length {len(thm_dc)}; the positional "
            f"correspondence cannot be reconciled",
            f"{theme_rel}#/dataColors",
        )
        return
    for i, (tok, thm) in enumerate(zip(tok_dc, thm_dc)):
        if tok != thm:
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"theme dataColors[{i}] {thm!r} does not match "
                f"the token declared value {tok!r}",
                f"{theme_rel}#/dataColors/{i}",
            )


def _reconcile(tokens_rel: str, theme_rel: str, ctx: RuleContext) -> Iterable[Finding]:
    tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
    theme_doc, herr = _load_json(ctx.repo_root / theme_rel)
    if terr is not None:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"design-tokens file could not be parsed ({terr}); "
            f"fidelity cannot be verified",
            f"{tokens_rel}#/",
        )
        return
    if herr is not None:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"theme file could not be parsed ({herr}); fidelity cannot be verified",
            f"{theme_rel}#/",
        )
        return
    colors = tokens_doc.get("colors", {}) if isinstance(tokens_doc, dict) else {}
    theme = theme_doc if isinstance(theme_doc, dict) else {}
    yield from _background_findings(colors, theme, theme_rel)
    yield from _data_colors_findings(colors, theme, theme_rel)


def _run_fidelity_check(
    ctx: RuleContext,
    rule_id: str,
    parse_error_suffix: str,
    reconcile: Callable[[str, str, RuleContext], Iterable[Finding]],
) -> list[Finding]:
    """Drive a fidelity rule over every committed tokens file.

    Shared by DL3 and DL8: for each tokens file, ERROR if it will not parse,
    else pair it to its theme and delegate to ``reconcile``. The only per-rule
    variation is the ``rule_id`` stamped on findings and the ``parse_error_suffix``
    naming which fidelity the failed parse blocks.
    """
    findings: list[Finding] = []
    for tokens_rel in _iter_tokens_files(ctx):
        tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
        if terr is not None:
            findings.append(
                Finding(
                    rule_id,
                    Severity.ERROR,
                    f"design-tokens file could not be parsed ({terr}); "
                    f"{parse_error_suffix}",
                    f"{tokens_rel}#/",
                )
            )
            continue
        theme_rel = _theme_rel_for(tokens_rel, tokens_doc, ctx)
        if theme_rel is None:
            continue
        findings.extend(reconcile(tokens_rel, theme_rel, ctx))
    return findings


@register(
    RULE_ID, "Theme styling values are faithful to the design tokens they compile from"
)
def check_theme_fidelity(ctx: RuleContext) -> Iterable[Finding]:
    return _run_fidelity_check(ctx, RULE_ID, "fidelity cannot be verified", _reconcile)


# --- DL8: sentiment 4->3 fidelity (opt-in, human-declared correspondence) -----
#
# DL3 above deliberately never reconciles sentiment (a 4->3 naming ambiguity a
# human must resolve). DL8 is the follow-on rule that ruling unlocks: it reads
# an opt-in ``meta.sentiment_map`` -- a human-frozen ``{tokens_key: theme_key}``
# correspondence -- and FLAGS any mismatch. Absent the map, DL8 is provably
# inert (no finding, ever): it never guesses which tokens sentiment key
# corresponds to which theme key. Own rule id (Principle V hard rule #9: two
# rules must never share one id) -- DL8, not DL3.

SENTIMENT_RULE_ID = "DL8"


def _raw_sentiment_map(tokens_doc: Any) -> Any:
    """The raw ``meta.sentiment_map`` value as committed, or None if the key is
    absent entirely.

    Lets the caller tell "no map declared" (None) apart from "map declared but
    malformed" (a present-but-invalid value) -- the latter must ERROR, never be
    silently swallowed. Only ``meta.sentiment_map`` being wholly absent (or an
    unusable ``meta``) reads as "no opt-in".
    """
    if not isinstance(tokens_doc, dict):
        return None
    meta = tokens_doc.get("meta")
    if not isinstance(meta, dict):
        return None
    return meta.get("sentiment_map")


def _sentiment_map_for(tokens_doc: Any) -> dict[str, str] | None:
    """The human-declared ``{tokens_sentiment_key: theme_key}`` map, or None.

    None means "no usable map" -- EITHER no map declared OR one declared but
    malformed. Callers that must distinguish the two (to ERROR on a botched
    opt-in rather than silently skip) pair this with ``_raw_sentiment_map``.
    DL8 never infers this map from color proximity or key names; it only
    reads what a human has already written to ``meta.sentiment_map``.
    """
    raw = _raw_sentiment_map(tokens_doc)
    if not isinstance(raw, dict) or not raw:
        return None
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in raw.items()):
        return None
    return raw


def _malformed_sentiment_map_findings(
    tokens_rel: str, tokens_doc: Any
) -> Iterable[Finding]:
    """One ERROR when meta.sentiment_map is declared but unusable, else nothing.

    Distinguishes "no map declared" (raw absent -> inert, refuse to invent one)
    from "declared but malformed" (a blank/non-string entry, an empty map): the
    latter must ERROR, because silently treating a botched opt-in as absent
    would disable the guard the author asked for while the theme-spec still
    claims fidelity is verified.
    """
    raw = _raw_sentiment_map(tokens_doc)
    if raw is None:
        return
    yield Finding(
        SENTIMENT_RULE_ID,
        Severity.ERROR,
        f"meta.sentiment_map is declared but malformed -- it must be a "
        f"non-empty mapping of string tokens-key -> string theme-key, "
        f"got {raw!r}; sentiment fidelity cannot be verified",
        f"{tokens_rel}#/meta/sentiment_map",
    )


@dataclass(frozen=True)
class _SentimentSides:
    """The two value sources plus locator base a sentiment_map entry reconciles
    against -- the loop-invariant context shared across every declared entry."""

    tok_sentiment: dict
    theme: dict
    theme_rel: str


def _sentiment_entry_findings(
    tok_key: str, thm_key: str, sides: _SentimentSides
) -> Iterable[Finding]:
    """One ERROR when a single declared map entry fails to reconcile, else none."""
    tok_val = sides.tok_sentiment.get(tok_key)
    thm_val = sides.theme.get(thm_key)
    if tok_val is None or thm_val is None:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"declared sentiment_map entry {tok_key!r} -> {thm_key!r} "
            f"cannot be reconciled: "
            f"colors.sentiment.{tok_key} is "
            f"{'absent' if tok_val is None else tok_val!r}, "
            f"theme.{thm_key} is "
            f"{'absent' if thm_val is None else thm_val!r}",
            f"{sides.theme_rel}#/{thm_key}",
        )
        return
    if tok_val != thm_val:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"theme {thm_key} {thm_val!r} does not match the token "
            f"declared sentiment.{tok_key} value {tok_val!r} "
            f"(declared correspondence {tok_key!r} -> {thm_key!r})",
            f"{sides.theme_rel}#/{thm_key}",
        )


def _reconcile_sentiment(
    tokens_rel: str, theme_rel: str, ctx: RuleContext
) -> Iterable[Finding]:
    tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
    if terr is not None:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"design-tokens file could not be parsed ({terr}); sentiment "
            f"fidelity cannot be verified",
            f"{tokens_rel}#/",
        )
        return
    sentiment_map = _sentiment_map_for(tokens_doc)
    if sentiment_map is None:
        yield from _malformed_sentiment_map_findings(tokens_rel, tokens_doc)
        return  # no usable correspondence -- refuse to invent one
    theme_doc, herr = _load_json(ctx.repo_root / theme_rel)
    if herr is not None:
        yield Finding(
            SENTIMENT_RULE_ID,
            Severity.ERROR,
            f"theme file could not be parsed ({herr}); sentiment fidelity "
            f"cannot be verified",
            f"{theme_rel}#/",
        )
        return
    colors = tokens_doc.get("colors", {}) if isinstance(tokens_doc, dict) else {}
    tok_sentiment = colors.get("sentiment", {})
    tok_sentiment = tok_sentiment if isinstance(tok_sentiment, dict) else {}
    theme = theme_doc if isinstance(theme_doc, dict) else {}
    sides = _SentimentSides(tok_sentiment, theme, theme_rel)
    for tok_key, thm_key in sentiment_map.items():
        yield from _sentiment_entry_findings(tok_key, thm_key, sides)


@register(
    SENTIMENT_RULE_ID,
    "Theme sentiment colors are faithful to a human-declared sentiment_map",
)
def check_sentiment_fidelity(ctx: RuleContext) -> Iterable[Finding]:
    return _run_fidelity_check(
        ctx,
        SENTIMENT_RULE_ID,
        "sentiment fidelity cannot be verified",
        _reconcile_sentiment,
    )
