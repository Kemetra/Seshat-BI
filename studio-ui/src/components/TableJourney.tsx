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

/** A status that lets the NEXT stage begin. ONLY `pass`. */
function permitsSuccessor(status: StageState["status"]): boolean {
  // `docs/readiness/readiness-model.md` carries TWO rules, and reading only the second
  // is what produced two wrong revisions of this function:
  //
  //   "A stage may be entered only when the **prior stage is `pass`**"
  //   "`warning` does not block the next stage by itself; a `blocked` does."
  //
  // They do not conflict. Entry requires `pass`; `warning` is simply not the permanent
  // barrier `blocked` is -- it can be cleared to `pass` by accepting the deviation. The
  // engine settles which one governs entry: `run_next._stage_decision` walks the stages
  // in order and STOPS at a `warning`, returning that stage as the next action, so the
  // frontier has not moved past it.
  //
  // Treating `warning` as permitting a successor showed later work as available and
  // would have sent the analyst past the recorded readiness stage.
  return status === "pass";
}

/**
 * The nearest earlier stage that has not cleared, or null when the way is open.
 *
 * Derived from EVERY prerequisite, not from the current stage alone. Two revisions got
 * this wrong in opposite directions: locking on any non-`pass` current status fabricated
 * obstacles on a `warning` stage, and then keying only on `blocked` reported Silver as
 * open when Mapping had not started -- telling the analyst work was available when it was
 * not. Both are misrepresentations of the same authority.
 */
function blockingPrerequisite(
  stage: ReadinessStage,
  byStage: ReadonlyMap<ReadinessStage, StageState>,
): ReadinessStage | null {
  const index = STAGE_ORDER.indexOf(stage);
  if (index <= 0) return null;
  // Nearest first: the analyst needs the gate immediately in front of this stage, not
  // the earliest problem in the table's history.
  for (let earlier = index - 1; earlier >= 0; earlier -= 1) {
    const candidate = STAGE_ORDER[earlier];
    if (candidate === undefined) continue;
    const state = byStage.get(candidate);
    if (state !== undefined && !permitsSuccessor(state.status)) return candidate;
  }
  return null;
}

/**
 * ALL committed prose is technical. The default is inverted on purpose.
 *
 * A previous revision asked "does this string LOOK technical?" with a regex over paths,
 * file extensions, and command names. That is an arms race the projection wins: real
 * committed text also carries skill names (`retail-semantic-check`), model paths
 * (`powerbi/RetailStoreSales.SemanticModel`), stage identifiers (`publish_ready`), and
 * feature ids (`F016`) -- none of which share a lexical form worth matching. Every
 * widening of the pattern left another leak.
 *
 * So the rule is structural rather than lexical: text the SERVER supplied is technical and
 * belongs behind the disclosure; only wording the frontend authored appears in the primary
 * journey. That is a closed rule a reviewer can check by reading, and it satisfies FR-032
 * for text nobody has thought of yet.
 *
 * The cost is that genuinely readable committed prose is also hidden. That is the right
 * trade: FR-032 governs what the analyst is shown up front, and a summary plus a
 * disclosure loses nothing, while a leak misrepresents the product's whole promise.
 */

/** Count-only summary, so hidden evidence is still known to EXIST. */
function evidenceSummary(count: number): string {
  return count === 1 ? "1 committed reference" : `${count} committed references`;
}

function StageEvidence({ stage }: { stage: StageState }): React.JSX.Element | null {
  if (stage.evidence.length === 0) return null;
  const pending = stage.evidence.filter(
    (item) => item.live_state === "pending_live_profile",
  ).length;
  return (
    <ul className="journey__evidence">
      <li className="journey__summary">
        {evidenceSummary(stage.evidence.length)} recorded; see technical detail.
      </li>
      {pending > 0 && (
        // The [PENDING LIVE PROFILE] distinction the contract's `live_state` carries:
        // evidence awaiting a live run must never read as verified, so it is surfaced up
        // front even though the reference itself is not.
        <li className="journey__pending">
          {pending === 1 ? "1 reference awaits" : `${pending} references await`} a live
          check.
        </li>
      )}
    </ul>
  );
}

function StageBlockers({ stage }: { stage: StageState }): React.JSX.Element | null {
  if (stage.blocking_reasons.length === 0) return null;
  return (
    <ul className="journey__blockers">
      {stage.blocking_reasons.map((reason, index) => (
        <li key={`${reason.code ?? "reason"}:${index}`}>
          A recorded blocker needs attention; see technical detail.
        </li>
      ))}
    </ul>
  );
}

/** Every raw reference for one stage, behind the disclosure FR-032 requires. */
function StageTechnicalDetail({ stage }: { stage: StageState }): React.JSX.Element | null {
  const references = [
    ...stage.evidence.map((item) => item.source_ref),
    // The verbatim blocker PROSE, not just its source file: the primary journey shows a
    // summary when the message is technical, so the real text has to live somewhere.
    ...stage.blocking_reasons.map((reason) => reason.message),
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
  waitingOn,
}: {
  stage: StageState;
  position: Position;
  waitingOn: ReadinessStage | null;
}): React.JSX.Element {
  const label = stageLabel(stage.stage);
  return (
    <li
      // `aria-label` gives the item an accessible NAME, which is what lets a
      // screen-reader user (and these tests) address one stage among seven.
      aria-label={label}
      aria-current={position === "current" ? "step" : undefined}
      data-locked={String(waitingOn !== null)}
      className="journey__stage"
    >
      <StatusBadge status={stage.status} stage={stage.stage} />
      {waitingOn !== null && (
        <p className="journey__locked">Waiting for {stageLabel(waitingOn)} to clear.</p>
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
      {/* `_next_action` copies the committed instruction VERBATIM, and real ones name
          approval files and commands. Summarised here; the exact wording is disclosed. */}
      {/* Not "a step is WAITING". `retail_store_sales` has all seven stages passing and a
          committed `next_action` whose text says no further readiness action is required,
          so announcing unfinished work would contradict the record. Classifying
          terminal-vs-actionable would mean parsing the prose -- the same arms race the
          technical-text heuristic lost -- so the wording states only what is certain:
          a next action is recorded, and here it is. */}
      <p>A next action is recorded for this table; see technical detail for its wording.</p>
      <details className="journey__detail">
        <summary>Technical detail</summary>
        <p>{action.label}</p>
      </details>
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
  const byStage = new Map(journey.stages.map((stage) => [stage.stage, stage]));

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
        {journey.stages.map((stage) => (
          <StageItem
            key={stage.stage}
            stage={stage}
            position={positionOf(stage.stage, journey.current_stage)}
            waitingOn={blockingPrerequisite(stage.stage, byStage)}
          />
        ))}
      </ol>
      <ForbiddenScope scope={journey.forbidden_scope} />
      <NextAction journey={journey} />
    </div>
  );
}
