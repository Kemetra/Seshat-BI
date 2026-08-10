/**
 * One stage's categorical status (FR-008, FR-009, FR-031).
 *
 * Three signals carry the same meaning, on purpose:
 *   1. a colour, from the tokens;
 *   2. a text LABEL, so status never depends on hue -- WCAG 2.2 AA's
 *      non-colour requirement, and the reason a colour-blind or greyscale reader is
 *      not excluded;
 *   3. a leading glyph, which survives even when CSS fails to load.
 *
 * There is no numeric score and no progress percentage: FR-009 forbids a numeric
 * readiness, health, confidence, completeness, or maturity signal, and a bar filled
 * "4 of 7 stages" would be exactly that in visual form.
 */

import type * as React from "react";
import type { StageState } from "../api/types";
import "./StatusBadge.css";

type Status = StageState["status"];

/** The human wording for each status, and the glyph that carries it without colour. */
const PRESENTATION: Record<Status, { label: string; glyph: string; hint: string }> = {
  pass: { label: "Passed", glyph: "✓", hint: "This stage is complete with evidence." },
  warning: {
    label: "Advanced with a recorded issue",
    glyph: "!",
    // Deliberately not "nearly passed": `warning` means advanced WITH a recorded
    // issue -- a static warning or an accepted deviation -- and softening it would
    // misrepresent a governance state.
    hint: "This stage advanced, and an issue is recorded against it.",
  },
  blocked: {
    label: "Blocked",
    glyph: "×",
    hint: "This stage cannot advance until its blockers are cleared.",
  },
  not_started: {
    label: "Not started",
    glyph: "–",
    hint: "This stage has not begun.",
  },
};

/** Turn `mapping_ready` into `Mapping` -- a stage name, never a command name (FR-032). */
export function stageLabel(stage: string): string {
  const withoutSuffix = stage.replace(/_ready$/, "").replace(/_/g, " ");
  return withoutSuffix.charAt(0).toUpperCase() + withoutSuffix.slice(1);
}

export function StatusBadge({
  status,
  stage,
}: {
  status: Status;
  stage: string;
}): React.JSX.Element {
  const presentation = PRESENTATION[status];
  return (
    <p className="status-badge" data-status={status}>
      {/* The glyph is decorative: the label beside it already says the status, so
          announcing the character too would just be noise. */}
      <span className="status-badge__glyph" aria-hidden="true">
        {presentation.glyph}
      </span>
      <span className="status-badge__stage">{stageLabel(stage)}</span>
      <span className="status-badge__label">{presentation.label}</span>
      <span className="visually-hidden">{presentation.hint}</span>
    </p>
  );
}
