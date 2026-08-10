/**
 * The Studio shell (T012).
 *
 * Loads the deterministic workspace projection and renders one of four honest states:
 * loading, a request problem, a first-arrival workspace with no tables, or the table
 * list. The Command Room's detail views arrive with T013 -- this shell is the frame
 * they hang in, and it says what it is rather than pretending to more.
 *
 * FR-032: no command names, skill names, protocol messages, or raw file paths appear
 * here. FR-009: no numeric score is rendered, ever -- the status word and its evidence
 * are the whole signal.
 */

import type * as React from "react";
import { useEffect, useState } from "react";

import { StudioRequestError, fetchWorkspace } from "./api/client";
import type { WorkspaceSnapshot } from "./api/types";
import { StatusBadge } from "./components/StatusBadge";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; snapshot: WorkspaceSnapshot }
  | { kind: "problem"; message: string; recovery: string | null };

export function App(): React.JSX.Element {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchWorkspace()
      .then((snapshot) => {
        if (!cancelled) setState({ kind: "ready", snapshot });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const failure =
          error instanceof StudioRequestError
            ? { message: error.message, recovery: error.recoveryAction }
            : { message: "Studio could not read this workspace.", recovery: null };
        setState({ kind: "problem", ...failure });
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
 * FR-010's defects, surfaced rather than swallowed.
 *
 * A malformed committed input is the analyst's problem to fix, so it is shown with its
 * recovery action -- not logged and hidden behind a shorter table list.
 */
function InputDefects({ snapshot }: { snapshot: WorkspaceSnapshot }): React.JSX.Element {
  return (
    <section aria-labelledby="defects-heading">
      <h2 id="defects-heading">Input needs attention</h2>
      <ul>
        {snapshot.input_defects.map((defect) => (
          <li key={`${defect.code}:${defect.source_ref ?? ""}`}>
            <p>{defect.message}</p>
            <p>{defect.recovery_action}</p>
          </li>
        ))}
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
      <ul>
        {snapshot.tables.map((table) => {
          const current = table.stages.find(
            (stage) => stage.stage === table.current_stage,
          );
          return (
            <li key={table.table_id}>
              <h3>{table.display_name}</h3>
              {current !== undefined ? (
                <StatusBadge status={current.status} stage={current.stage} />
              ) : (
                <p>This table has not reported a current stage.</p>
              )}
              {table.next_action != null && <p>{table.next_action.label}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
