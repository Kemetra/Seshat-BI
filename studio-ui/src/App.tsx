/**
 * The Studio shell and Command Room (T012 shell, T013 detail).
 *
 * Loads the deterministic workspace projection and renders one of four honest states:
 * loading, a request problem, a first-arrival workspace with no tables, or the table
 * list -- each table showing its full seven-stage journey via `TableJourney`.
 *
 * FR-032: no command names, skill names, protocol messages, or raw file paths appear in
 * the primary journey; the server's own governance wording, which legitimately names
 * files and commands, lives behind an explicit disclosure. FR-009: no numeric score is
 * rendered, ever -- the status word and its evidence are the whole signal.
 */

import type * as React from "react";
import { useEffect, useState } from "react";

import { StudioRequestError, fetchWorkspace } from "./api/client";
import type { WorkspaceSnapshot } from "./api/types";
import { AgentHealthNotice } from "./components/AgentHealth";
import { TableJourney } from "./components/TableJourney";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; snapshot: WorkspaceSnapshot }
  | { kind: "problem"; message: string; recovery: string | null };

/** Describe a failed load without leaking an exception's internals to the interface. */
function describeFailure(error: unknown): { message: string; recovery: string | null } {
  if (error instanceof StudioRequestError) {
    return { message: error.message, recovery: error.recoveryAction };
  }
  return { message: "Studio could not read this workspace.", recovery: null };
}

/**
 * Load the workspace projection once, ignoring a response that arrives after unmount.
 *
 * Extracted from the component so `App` only decides what to RENDER: the cancellation
 * bookkeeping is the kind of detail that makes a render function hard to read and hard
 * to reason about.
 */
function useWorkspaceSnapshot(): LoadState {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchWorkspace()
      .then((snapshot) => {
        if (!cancelled) setState({ kind: "ready", snapshot });
      })
      .catch((error: unknown) => {
        if (!cancelled) setState({ kind: "problem", ...describeFailure(error) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

export function App(): React.JSX.Element {
  const state = useWorkspaceSnapshot();

  if (state.kind === "loading") {
    return (
      <main aria-busy="true">
        <h1>Seshat Studio</h1>
        <p>Reading this workspace…</p>
      </main>
    );
  }

  if (state.kind === "problem") {
    return (
      <main>
        <h1>Seshat Studio</h1>
        {/* `role="alert"` so a screen reader announces the failure without the user
            having to go looking for it. */}
        <div role="alert">
          <h2>This workspace could not be read</h2>
          <p>{state.message}</p>
          {state.recovery !== null && <p>{state.recovery}</p>}
        </div>
      </main>
    );
  }

  const { snapshot } = state;
  return (
    <main>
      <h1>{snapshot.identity.display_name}</h1>
      {/* Strictly additive: FR-025 requires the deterministic views below to stay
          usable in EVERY agent state, so this notice never gates what follows. */}
      <AgentHealthNotice health={snapshot.agent_health} />
      <PendingDecisions count={snapshot.pending_decision_count} />
      {snapshot.input_defects.length > 0 && <InputDefects snapshot={snapshot} />}
      {snapshot.tables.length === 0 ? (
        <FirstArrival />
      ) : (
        <TableList snapshot={snapshot} />
      )}
    </main>
  );
}

/**
 * How many business decisions await a named human (US1).
 *
 * US1 requires the Command Room to explain the "pending decision count" alongside the
 * stage, blockers, evidence, and next action. A QUEUE LENGTH is not a readiness signal,
 * so FR-009 does not forbid the number -- but the wording has to make that unmistakable,
 * because a bare figure next to a readiness journey invites reading it as a score.
 *
 * Foundation cannot record these decisions (FR-022, and `BootstrapState` types the
 * capability as the literal `false`), so this states the count and stops there.
 */
function PendingDecisions({ count }: { count: number }): React.JSX.Element {
  if (count === 0) {
    return (
      <p className="pending-decisions">
        No decisions are waiting on a named human.
      </p>
    );
  }
  // `1 decisions await` reads as carelessness, and an interface asking to be trusted
  // about readiness cannot afford sloppiness in the sentence beside the number.
  const noun = count === 1 ? "decision awaits" : "decisions await";
  return (
    <p className="pending-decisions">
      {`${count} ${noun} a named human's approval.`}
    </p>
  );
}

/**
 * Plain-language wording per defect code, keyed off the server's `code`.
 *
 * FR-010's defects are surfaced rather than swallowed: a malformed committed input is
 * the analyst's problem to fix, so it appears with a recovery action instead of being
 * hidden behind a silently shorter table list.
 *
 * FR-032 requires command names, skill names, protocol messages, and raw file paths to
 * be ABSENT from the primary journey "unless technical detail is explicitly opened".
 * The server's own `message`/`recovery_action` legitimately name
 * `templates/readiness-status.yaml` and `` `seshat check` `` -- correct for a
 * governance record, and exactly what FR-032 keeps out of the analyst's first screen.
 * So the primary text is written here, and the server's strings move behind a
 * disclosure the analyst opens on purpose.
 *
 * Keyed on `code` rather than pattern-matching the prose: the code is the stable
 * contract field, and a message reworded upstream must not silently fall back to
 * showing raw paths.
 */
const DEFECT_WORDING: Record<string, { summary: string; guidance: string }> = {
  unreadable_readiness_file: {
    summary: "One table's readiness record could not be read.",
    guidance:
      "Its file is not valid, so this table cannot be shown. Ask whoever maintains " +
      "this workspace to repair the record.",
  },
  incomplete_readiness_stages: {
    summary: "One table's readiness record is missing part of its journey.",
    guidance:
      "Some stages are absent from the record, so their state is unknown rather " +
      "than not started. The missing stages need to be added.",
  },
  unrecognized_stage_status: {
    summary: "One stage records a status Studio does not recognise.",
    guidance:
      "The status is not one of the four Studio understands, so the stage is shown " +
      "as unknown. The recorded value needs correcting.",
  },
};

function defectWording(code: string): { summary: string; guidance: string } {
  return (
    DEFECT_WORDING[code] ?? {
      summary: "A committed input needs attention.",
      guidance:
        "Studio could not use part of this workspace's recorded state. Open the " +
        "technical detail below, or ask whoever maintains this workspace.",
    }
  );
}

function InputDefects({ snapshot }: { snapshot: WorkspaceSnapshot }): React.JSX.Element {
  return (
    <section aria-labelledby="defects-heading">
      <h2 id="defects-heading">Input needs attention</h2>
      <ul>
        {snapshot.input_defects.map((defect) => {
          const wording = defectWording(defect.code);
          return (
            <li key={`${defect.code}:${defect.source_ref ?? ""}`}>
              <p>{wording.summary}</p>
              <p>{wording.guidance}</p>
              {/* `<details>` is the explicit opening FR-032 allows: keyboard
                  reachable, announced as a disclosure, and closed by default. */}
              <details>
                <summary>Technical detail</summary>
                <p>{defect.message}</p>
                <p>{defect.recovery_action}</p>
                {defect.source_ref !== null && <p>{defect.source_ref}</p>}
              </details>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** A recognised workspace with nothing onboarded yet -- a real state, not an error. */
function FirstArrival(): React.JSX.Element {
  return (
    <section aria-labelledby="first-arrival-heading">
      <h2 id="first-arrival-heading">No tables are onboarded yet</h2>
      <p>
        This workspace is recognised but has no tables to show. Onboard a source table
        to see its readiness journey here.
      </p>
    </section>
  );
}

function TableList({ snapshot }: { snapshot: WorkspaceSnapshot }): React.JSX.Element {
  return (
    <section aria-labelledby="tables-heading">
      <h2 id="tables-heading">Tables</h2>
      <ul className="table-list">
        {snapshot.tables.map((table) => (
          <li key={table.table_id}>
            <h3>{table.display_name}</h3>
            {/* The full seven-stage journey, not just the current badge: US1 requires
                the Command Room to explain the current stage, its blockers, its
                evidence, and the next allowed action. */}
            <TableJourney journey={table} />
          </li>
        ))}
      </ul>
    </section>
  );
}
