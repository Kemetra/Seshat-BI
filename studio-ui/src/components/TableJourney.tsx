/**
 * One table's seven-stage readiness journey (T013, US1).
 *
 * US1 scenario 2 is the demanding one: "it names Mapping as current, shows the concrete
 * blocker and evidence, offers the mapping action, and leaves Silver and later work
 * LOCKED."
 *
 * **How "locked" is expressed without inventing a status.** FR-008 pins the vocabulary
 * to four categorical values, so a gated stage is still `not_started` -- that is the
 * truth the authority recorded. What the analyst additionally needs is WHY: not started
 * because the gate ahead is closed, rather than because nobody got round to it. That is
 * derived purely from POSITION relative to the current stage, added as a separate
 * signal, and never written back into `status`.
 *
 * FR-032: stage identifiers are shown as human labels ("Mapping", not `mapping_ready`),
 * and every raw source reference lives behind an explicit disclosure. FR-009: no
 * percentage, ratio, or score -- the status word and its evidence are the whole signal.
 */

import type * as React from "react";

import type { ReadinessStage, StageState, TableJourney as Journey } from "../api/types";
import { StatusBadge, stageLabel } from "./StatusBadge";
import "./TableJourney.css";

/** Where a stage sits relative to the table's current position. */
type Position = "behind" | "current" | "ahead";

/**
 * The canonical stage order, matching `seshat.status_surface._STAGE_ORDER`.
 *
 * Position is derived from THIS, not from the order the stages happened to arrive in.
 * The contract pins the array's length at seven but says nothing about its ordering, so
 * a server that reordered would otherwise invert the gating signal entirely -- a passed
 * prerequisite reporting locked, and ungated later work reporting open.
 */
const STAGE_ORDER: readonly ReadinessStage[] = [
  "source_ready",
  "mapping_ready",
  "silver_ready",
  "gold_ready",
  "semantic_model_ready",
  "dashboard_ready",
  "publish_ready",
];

function positionOf(stage: ReadinessStage, current: ReadinessStage | null): Position {
  if (current === null) return "behind";
  const stageIndex = STAGE_ORDER.indexOf(stage);
  const currentIndex = STAGE_ORDER.indexOf(current);
  // An unrecognised current stage is server drift, not a position: treat nothing as
  // gated rather than inventing an ordering from an unknown value.
  if (currentIndex === -1 || stageIndex === -1) return "behind";
  if (stageIndex === currentIndex) return "current";
  return stageIndex < currentIndex ? "behind" : "ahead";
}

/**
 * True when a stage is gated by an earlier stage that has not cleared.
 *
 * ONLY `blocked` gates. The readiness model is explicit -- "`blocked` stops the next
 * stage, `warning` does not" (`docs/readiness/readiness-model.md`) -- and `run_next`
 * routes `warning` down the proceed path. An earlier revision locked on any non-`pass`
 * status, so a `warning` current stage, which is what a clean live run assigns and
 * therefore the commonest non-pass state, fabricated locks on every later stage. That is
 * exactly the invented obstacle this component must never show.
 */
function isLocked(position: Position, currentStatus: StageState["status"] | null): boolean {
  return position === "ahead" && currentStatus === "blocked";
}

function StageEvidence({ stage }: { stage: StageState }): React.JSX.Element | null {
  if (stage.evidence.length === 0) return null;
  return (
    <ul className="journey__evidence">
      {stage.evidence.map((item) => (
        <li key={item.source_ref}>
          {item.label}
          {/* The [PENDING LIVE PROFILE] distinction the contract's `live_state` carries:
              evidence awaiting a live run must not read as verified. */}
          {item.live_state === "pending_live_profile" && (
            <span className="journey__pending"> (awaiting a live check)</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function StageBlockers({ stage }: { stage: StageState }): React.JSX.Element | null {
  if (stage.blocking_reasons.length === 0) return null;
  return (
    <ul className="journey__blockers">
      {stage.blocking_reasons.map((reason, index) => (
        <li key={`${reason.code ?? "reason"}:${index}`}>{reason.message}</li>
      ))}
    </ul>
  );
}

/** Every raw reference for one stage, behind the disclosure FR-032 requires. */
function StageTechnicalDetail({ stage }: { stage: StageState }): React.JSX.Element | null {
  const references = [
    ...stage.evidence.map((item) => item.source_ref),
    ...stage.blocking_reasons
      .map((reason) => reason.source_ref)
      .filter((ref): ref is string => ref !== null),
  ];
  // The early return must consider the AUTHORITY too. Keyed on references alone, a stage
  // carrying `required_authority` but nothing to cite dropped it silently -- and FR-008
  // names required authority among the six fields that MUST be preserved.
  if (references.length === 0 && stage.required_authority.length === 0) return null;

  return (
    <details className="journey__detail">
      <summary>Technical detail</summary>
      {references.length > 0 && (
        <ul>
          {references.map((reference) => (
            <li key={reference}>{reference}</li>
          ))}
        </ul>
      )}
      {stage.required_authority.length > 0 && (
        <p>Requires: {stage.required_authority.join(", ")}</p>
      )}
    </details>
  );
}

/**
 * What this table may not advance into yet (FR-008's `forbidden_scope`).
 *
 * The projection sends it and the UI previously dropped it, losing one of the six fields
 * FR-008 requires to be preserved. Rendered as prose rather than as a locked-stage
 * marker: forbidden scope is the authority's own statement about permitted work, not a
 * position Studio derives.
 */
function ForbiddenScope({ scope }: { scope: readonly string[] }): React.JSX.Element | null {
  if (scope.length === 0) return null;
  return (
    <p className="journey__forbidden">
      Not permitted yet for this table: {scope.join(", ")}.
    </p>
  );
}

function StageItem({
  stage,
  position,
  locked,
  currentLabel,
}: {
  stage: StageState;
  position: Position;
  locked: boolean;
  currentLabel: string | null;
}): React.JSX.Element {
  const label = stageLabel(stage.stage);
  return (
    <li
      // `aria-label` gives the item an accessible NAME, which is what lets a
      // screen-reader user (and these tests) address one stage among seven.
      aria-label={label}
      aria-current={position === "current" ? "step" : undefined}
      data-locked={String(locked)}
      className="journey__stage"
    >
      <StatusBadge status={stage.status} stage={stage.stage} />
      {locked && currentLabel !== null && (
        <p className="journey__locked">Waiting for {currentLabel} to clear.</p>
      )}
      <StageEvidence stage={stage} />
      <StageBlockers stage={stage} />
      <StageTechnicalDetail stage={stage} />
    </li>
  );
}

function NextAction({ journey }: { journey: Journey }): React.JSX.Element | null {
  const action = journey.next_action;
  if (action == null) return null;
  return (
    <section className="journey__next" aria-labelledby={`${journey.table_id}-next`}>
      <h4 id={`${journey.table_id}-next`}>Next</h4>
      <p>{action.label}</p>
      {action.requires_named_human && (
        <p className="journey__authority">
          A named human must approve this step; Studio cannot.
        </p>
      )}
    </section>
  );
}

export function TableJourney({ journey }: { journey: Journey }): React.JSX.Element {
  const current =
    journey.stages.find((stage) => stage.stage === journey.current_stage) ?? null;

  return (
    <div className="journey">
      {/* `current === null` covers BOTH an absent `current_stage` and one naming a stage
          the payload does not contain. Testing the raw field instead left server drift
          silent: no current marker AND no explanation, which reads as a table that
          simply has not started. */}
      {current === null && <p>This table has not reported a current stage.</p>}
      {/* An ORDERED list: the sequence is part of the meaning, so it belongs in the
          markup rather than in visual position, where a screen-reader user cannot
          perceive it. */}
      {/* Named so a test -- and a screen-reader user -- can address the STAGE list
          specifically, rather than whichever list happens to be first in the DOM. */}
      <ol className="journey__stages" aria-label="Readiness stages">
        {journey.stages.map((stage) => {
          const position = positionOf(stage.stage, journey.current_stage);
          return (
            <StageItem
              key={stage.stage}
              stage={stage}
              position={position}
              locked={isLocked(position, current?.status ?? null)}
              currentLabel={current === null ? null : stageLabel(current.stage)}
            />
          );
        })}
      </ol>
      <ForbiddenScope scope={journey.forbidden_scope} />
      <NextAction journey={journey} />
    </div>
  );
}
