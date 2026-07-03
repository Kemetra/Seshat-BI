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

DELIBERATELY OUT OF SCOPE (a human ruling gates them, not this rule):
  * sentiment fidelity (tokens ``success``/``warning``/``danger`` vs theme
    ``good``/``neutral``/``bad``). The theme's middle slot is an amber that
    matches tokens ``warning`` BY COLOR but tokens ``neutral`` BY NAME -- a 4->3
    correspondence that is a genuine Principle-V ambiguity. DL3 surfaces the need
    for a ruling; it does not pick. When a human freezes that map (as DL1 froze
    its vocabulary), a follow-on rule can carry it.
  * ``text.primary`` -> theme ``foreground`` (same: no committed correspondence).

The pairing is generic: DL3 finds the tokens file by its ``meta.compiles_to``
field (the tokens declare their own theme target) and reconciles that pair. No
tenant/example/brand literal appears here (Principle VII); the field names
(``dataColors``, ``background``) are generic Power BI theme keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

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


def _theme_rel_for(tokens_rel: str, tokens_doc: Any, ctx: RuleContext) -> str | None:
    """Resolve the theme file this tokens file compiles to.

    Prefers the tokens' own ``meta.compiles_to`` (a human-declared target,
    resolved relative to the tokens file's directory). Falls back to a single
    committed ``*.theme.json`` when compiles_to is absent.
    """
    compiles_to = None
    if isinstance(tokens_doc, dict):
        meta = tokens_doc.get("meta")
        if isinstance(meta, dict):
            compiles_to = meta.get("compiles_to")
    if isinstance(compiles_to, str) and compiles_to:
        parent = tokens_rel.rsplit("/", 1)[0] if "/" in tokens_rel else ""
        # A compiles_to may be repo-relative (live) or dir-relative (fixture).
        candidates = [compiles_to]
        if parent:
            candidates.append(f"{parent}/{compiles_to}")
        for cand in candidates:
            if (ctx.repo_root / cand).exists():
                return cand
        return compiles_to
    themes = [
        p
        for p in ctx.tracked_files
        if p.endswith(_THEME_SUFFIX) and not is_test_path(p)
    ]
    return themes[0] if len(themes) == 1 else None


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

    # --- background (identity-named correspondence) ---
    tok_bg = colors.get("background")
    thm_bg = theme.get("background")
    if tok_bg is not None and thm_bg is not None and tok_bg != thm_bg:
        yield Finding(
            RULE_ID,
            Severity.ERROR,
            f"theme background {thm_bg!r} does not match the token "
            f"declared value {tok_bg!r}",
            f"{theme_rel}#/background",
        )

    # --- data_colors (positional, T029-declared correspondence) ---
    tok_dc = colors.get("data_colors")
    thm_dc = theme.get("dataColors")
    if isinstance(tok_dc, list) and not isinstance(thm_dc, list):
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
    elif isinstance(tok_dc, list) and isinstance(thm_dc, list):
        if len(tok_dc) != len(thm_dc):
            yield Finding(
                RULE_ID,
                Severity.ERROR,
                f"data_colors length {len(tok_dc)} does not match theme "
                f"dataColors length {len(thm_dc)}; the positional "
                f"correspondence cannot be reconciled",
                f"{theme_rel}#/dataColors",
            )
        else:
            for i, (tok, thm) in enumerate(zip(tok_dc, thm_dc)):
                if tok != thm:
                    yield Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"theme dataColors[{i}] {thm!r} does not match "
                        f"the token declared value {tok!r}",
                        f"{theme_rel}#/dataColors/{i}",
                    )


@register(
    RULE_ID, "Theme styling values are faithful to the design tokens they compile from"
)
def check_theme_fidelity(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for tokens_rel in _iter_tokens_files(ctx):
        tokens_doc, terr = _load_yaml(ctx.repo_root / tokens_rel)
        if terr is not None:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"design-tokens file could not be parsed ({terr}); "
                    f"fidelity cannot be verified",
                    f"{tokens_rel}#/",
                )
            )
            continue
        theme_rel = _theme_rel_for(tokens_rel, tokens_doc, ctx)
        if theme_rel is None:
            continue
        findings.extend(_reconcile(tokens_rel, theme_rel, ctx))
    return findings
