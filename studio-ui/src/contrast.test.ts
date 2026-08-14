/**
 * FR-031 contrast, computed from the tokens rather than eyeballed (T032).
 *
 * `tokens.css` claims "every `--status-*-fg` is chosen against `--surface` at 4.5:1 or
 * better, and the palette is defined once here so a contrast audit has a single place to
 * check." That audit was by eye, and a prose claim nobody can re-run is the weakest kind
 * of guarantee -- it cannot fail when someone edits a hex value.
 *
 * This is deliberately NOT a replacement for axe's `color-contrast` rule, which is a
 * different mechanism: axe needs real layout and paint to discover which pairs actually
 * meet, and jsdom paints nothing, so it reports `incomplete` there forever. What CAN be
 * decided without paint is whether the declared palette is capable of meeting AA at all.
 * A token pair below threshold is a violation no amount of layout can rescue, so
 * catching it here is strictly earlier than a browser pass would.
 *
 * The pairs audited are the ones that actually RENDER, which is a superset of what the
 * comment describes: each status foreground sits on its own `--status-*-bg`, not on
 * `--surface`. Both are checked -- the tinted panels use the former, and any status text
 * placed on the plain surface uses the latter.
 *
 * WCAG 2.2: 1.4.3 Contrast (Minimum) is 4.5:1 for normal text; 1.4.11 Non-text Contrast
 * is 3:1 for UI components and meaningful graphics.
 */

import { describe, expect, it } from "vitest";

/**
 * The palette text, inlined by `vitest.config.ts` at transform time.
 *
 * Both in-test routes were tried and rejected on evidence:
 *
 * * `import "./tokens.css?raw"` resolves to an EMPTY string under the suite's
 *   `css: false` (measured: length 0), which would silently score a palette of zero
 *   tokens. The "unresolved token is a failure" test below turns that into a red run
 *   rather than a false pass, but the audit still needs the real text.
 * * `node:fs` inside a test does not typecheck, because `tsconfig.json` deliberately
 *   ships no `@types/node` -- this project targets the browser, and widening the global
 *   type surface to all of Node so one test can read a file is the larger change.
 *
 * So the read happens in the config, which already runs on Node. There is still exactly
 * one copy of the palette on disk: `src/tokens.css`.
 */
declare const __TOKENS_CSS__: string;
const TOKENS: string = __TOKENS_CSS__;

/** Text needs 4.5:1 (WCAG 1.4.3); UI components and meaningful graphics need 3:1 (1.4.11). */
const TEXT_MINIMUM = 4.5;
const NON_TEXT_MINIMUM = 3;

/**
 * Hex tokens from one CSS block.
 *
 * Only `#rrggbb` values are collected. A token defined with a keyword or a `var()`
 * indirection is not a colour this audit can resolve, and silently scoring it would be
 * worse than leaving it out -- `missingTokens` below turns any such gap into a failure
 * rather than a quiet pass.
 */
function hexTokens(css: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const match of css.matchAll(/(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    const [, name, value] = match;
    // Both groups are non-optional in the pattern, so this only narrows for the compiler.
    if (name !== undefined && value !== undefined) {
      found[name] = value.toLowerCase();
    }
  }
  return found;
}

const DARK_QUERY = "@media (prefers-color-scheme: dark)";
const lightSource = TOKENS.slice(0, TOKENS.indexOf(DARK_QUERY));
const darkSource = TOKENS.slice(TOKENS.indexOf(DARK_QUERY));

const light = hexTokens(lightSource);
/**
 * Dark OVERRIDES light rather than replacing it wholesale. The dark block redefines only
 * the tokens that change, so a spread is what the cascade actually does -- scoring the
 * dark block alone would miss every inherited value and report phantom gaps.
 */
const dark = { ...light, ...hexTokens(darkSource) };

/** WCAG 2.x relative luminance. */
function relativeLuminance(hex: string): number {
  const channel = (offset: number): number => {
    const srgb = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
  };
  // Positional rather than destructured: a tuple index is `number | undefined` under
  // `noUncheckedIndexedAccess`, and the coefficients are the WCAG 2.x sRGB weights.
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

function contrastRatio(foreground: string, background: string): number {
  const a = relativeLuminance(foreground);
  const b = relativeLuminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

const STATUSES = ["pass", "warning", "blocked", "not-started"] as const;

/** Every pair that renders, with the threshold its content type earns. */
const PAIRS: ReadonlyArray<{
  foreground: string;
  background: string;
  minimum: number;
  note: string;
}> = [
  ...STATUSES.flatMap((status) => [
    {
      foreground: `--status-${status}-fg`,
      background: `--status-${status}-bg`,
      minimum: TEXT_MINIMUM,
      note: `${status} status text on its own tinted panel`,
    },
    {
      foreground: `--status-${status}-fg`,
      background: "--surface",
      minimum: TEXT_MINIMUM,
      note: `${status} status text on the plain surface`,
    },
  ]),
  { foreground: "--text", background: "--surface", minimum: TEXT_MINIMUM, note: "body text" },
  {
    foreground: "--text",
    background: "--surface-raised",
    minimum: TEXT_MINIMUM,
    note: "body text on a raised panel",
  },
  {
    foreground: "--text",
    background: "--surface-sunken",
    minimum: TEXT_MINIMUM,
    note: "body text on a sunken panel",
  },
  {
    foreground: "--text-muted",
    background: "--surface",
    minimum: TEXT_MINIMUM,
    note: "secondary text",
  },
  {
    foreground: "--text-muted",
    background: "--surface-raised",
    minimum: TEXT_MINIMUM,
    note: "secondary text on a raised panel",
  },
  {
    foreground: "--text-muted",
    background: "--surface-sunken",
    minimum: TEXT_MINIMUM,
    note: "secondary text on a sunken panel",
  },
  {
    foreground: "--focus-ring",
    background: "--surface",
    minimum: NON_TEXT_MINIMUM,
    note: "focus indicator (WCAG 1.4.11)",
  },
  {
    foreground: "--focus-ring",
    background: "--surface-raised",
    minimum: NON_TEXT_MINIMUM,
    note: "focus indicator on a raised panel (WCAG 1.4.11)",
  },
];

describe("FR-031 -- the declared palette can meet WCAG 2.2 AA", () => {
  it.each(["light", "dark"] as const)("%s scheme has no unresolved token", (scheme) => {
    const palette = scheme === "light" ? light : dark;
    const missing = [
      ...new Set(PAIRS.flatMap(({ foreground, background }) => [foreground, background])),
    ].filter((token) => palette[token] === undefined);

    // A pair whose token this audit cannot resolve must FAIL, never score as a pass.
    expect(missing).toEqual([]);
  });

  it.each(["light", "dark"] as const)("%s scheme meets every threshold", (scheme) => {
    const palette = scheme === "light" ? light : dark;

    /**
     * An unresolved token is a FAILURE, not a skip.
     *
     * `Record` indexing is `string | undefined` under strict TS, and the tempting fix is
     * a non-null assertion. That would turn a missing token into `NaN` comparisons that
     * silently satisfy `< minimum`, i.e. a renamed token would read as a pass. Naming the
     * absence keeps the audit honest -- the companion test above also pins it.
     */
    const failures = PAIRS.flatMap(({ foreground, background, minimum, note }) => {
      const fg = palette[foreground];
      const bg = palette[background];
      if (fg === undefined || bg === undefined) {
        return [`${note}: ${foreground} or ${background} is not a resolvable hex token`];
      }
      const ratio = contrastRatio(fg, bg);
      return ratio < minimum
        ? [
            `${note}: ${foreground} on ${background} is ${ratio.toFixed(2)}:1, ` +
              `needs ${minimum}:1`,
          ]
        : [];
    });

    expect(failures).toEqual([]);
  });

  it("both schemes define the status palette explicitly", () => {
    // A token defined only inside the dark media query borrows whatever the host paints
    // when the query does not match -- the trap `tokens.css` names in its own header.
    const statusTokens = STATUSES.flatMap((status) => [
      `--status-${status}-fg`,
      `--status-${status}-bg`,
    ]);
    const lightOnly = hexTokens(lightSource);
    const darkOnly = hexTokens(darkSource);

    expect(statusTokens.filter((token) => lightOnly[token] === undefined)).toEqual([]);
    expect(statusTokens.filter((token) => darkOnly[token] === undefined)).toEqual([]);
  });

  it("the ratio computation agrees with the WCAG reference extremes", () => {
    // Without this, a broken luminance formula could report everything as passing and
    // the suite above would be a rubber stamp. Black on white is the documented 21:1
    // maximum, and any colour against itself is exactly 1:1.
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(contrastRatio("#ffffff", "#ffffff")).toBeCloseTo(1, 5);
    // #767676 on white is the canonical DARKEST-passing grey: 4.54:1. One step lighter
    // (#777777) is 4.48:1 and fails. Pinning both sides of that boundary is what proves
    // the formula is calibrated rather than merely monotonic -- an implementation off by
    // a few percent would still order colours correctly and pass a one-sided check.
    expect(contrastRatio("#767676", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio("#777777", "#ffffff")).toBeLessThan(4.5);
  });
});
