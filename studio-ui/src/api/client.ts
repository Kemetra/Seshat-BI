/**
 * The only place the browser talks to Studio.
 *
 * Every request is same-origin and credentialed: the session lives in an HttpOnly
 * cookie the browser attaches itself, so no token is ever held in JavaScript. That is
 * why `credentials: "same-origin"` is set explicitly rather than left to the default --
 * an omitted cookie reads to the user as "logged out" and is confusing to diagnose.
 *
 * Relative URLs, deliberately: the loopback port is OS-assigned, so a hardcoded origin
 * would break on every launch. `base: "./"` in the Vite config keeps asset URLs
 * relative for the same reason.
 */

import type {
  AgentHealth,
  AgentThreadRef,
  BootstrapState,
  Problem,
  TableJourney,
  WorkspaceSnapshot,
} from "./types";

const API_PREFIX = "/api/v1";

/** A failed request, carrying the server's redacted problem document when there is one. */
export class StudioRequestError extends Error {
  readonly status: number;
  readonly problem: Problem | null;

  constructor(status: number, problem: Problem | null) {
    // The problem's own `detail` is already redacted and user-facing, so it makes a
    // better message than a generic "request failed".
    super(problem?.detail ?? `Studio request failed with status ${status}`);
    this.name = "StudioRequestError";
    this.status = status;
    this.problem = problem;
  }

  /** What the interface should tell the analyst to do next. */
  get recoveryAction(): string | null {
    return this.problem?.recovery_action ?? null;
  }
}

async function readProblem(response: Response): Promise<Problem | null> {
  try {
    return (await response.json()) as Problem;
  } catch {
    // A non-JSON error body is not itself a failure worth surfacing: the status code
    // still carries the meaning, and inventing a problem document would be fiction.
    return null;
  }
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new StudioRequestError(response.status, await readProblem(response));
  }
  return (await response.json()) as T;
}

export function fetchBootstrapState(): Promise<BootstrapState> {
  return get<BootstrapState>("/bootstrap/state");
}

export function fetchWorkspace(): Promise<WorkspaceSnapshot> {
  return get<WorkspaceSnapshot>("/workspace");
}

export function fetchTable(tableId: string): Promise<TableJourney> {
  // `encodeURIComponent` is the boundary here: a table id is workspace data, and the
  // server refuses a traversal-shaped id, but the browser must not build a malformed
  // URL that never reaches that check.
  return get<TableJourney>(`/tables/${encodeURIComponent(tableId)}`);
}

export function fetchAgentHealth(): Promise<AgentHealth> {
  return get<AgentHealth>("/agent/health");
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  // `exactOptionalPropertyTypes` forbids `body: undefined`, so the key is omitted
  // entirely for a bodyless POST rather than set to undefined.
  const init: RequestInit = {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_PREFIX}${path}`, init);
  if (!response.ok) {
    throw new StudioRequestError(response.status, await readProblem(response));
  }
  // 204 carries no body; parsing one would throw on a successful interrupt.
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Open a conversation. The browser attaches `Origin` itself, which step 2 requires. */
export function createThread(selectedTableId: string | null): Promise<AgentThreadRef> {
  return post<AgentThreadRef>("/agent/threads", {
    selected_table_id: selectedTableId,
  });
}

/**
 * Start one turn.
 *
 * `snapshot_revision` is sent so the server can tell whether the analyst was looking at
 * the current workspace when they asked. `read_only` is the default because proposing
 * changes is a mode the analyst opts into, never one inferred for them.
 */
export function startTurn(
  threadId: string,
  prompt: string,
  options: { snapshotRevision?: string; mode?: "read_only" | "propose_changes" } = {},
): Promise<{ turn_id: string }> {
  return post<{ turn_id: string }>(
    `/agent/threads/${encodeURIComponent(threadId)}/turns`,
    {
      prompt,
      snapshot_revision: options.snapshotRevision ?? "unknown",
      requested_mode: options.mode ?? "read_only",
    },
  );
}

/** Stop a live turn. A 409 means it had already ended, which is not an error to show. */
export function interruptTurn(threadId: string, turnId: string): Promise<void> {
  return post<void>(
    `/agent/threads/${encodeURIComponent(threadId)}/turns/` +
      `${encodeURIComponent(turnId)}/interrupt`,
  );
}

/** The contract's decision enum. Not booleans: a deny is a decision, not an absent allow. */
export type ApprovalDecision = "allow_once" | "deny";

/**
 * Relay one technical approval decision (FR-019, FR-020).
 *
 * **The browser performs no side effect.** This POSTs a decision and nothing else: the
 * ledger burns the id, the server answers the JSON-RPC request the provider blocks on,
 * and the turn continues. Nothing here writes a file, touches a provider, or decides
 * anything locally.
 *
 * The one-time property is the SERVER'S, not a disabled button. A caller that fires
 * twice gets a 409 on the second attempt, and that refusal -- not any client state -- is
 * what makes a replay impossible.
 *
 * Every failure is thrown as a `StudioRequestError` carrying the server's redacted
 * problem document, including two codes the OpenAPI does not yet document: **422** (a
 * decision value the server does not recognise, which is a bug in this client) and
 * **502** (recorded but NOT delivered -- the id is spent and the provider was never
 * answered, so the decision cannot be re-sent). Callers must not treat 502 as retryable.
 */
export function respondToToolApproval(
  threadId: string,
  approvalId: string,
  decision: ApprovalDecision,
): Promise<void> {
  return post<void>(
    `/agent/threads/${encodeURIComponent(threadId)}/approvals/` +
      `${encodeURIComponent(approvalId)}`,
    { decision },
  );
}

/**
 * Exchange the one-time bootstrap token for the session cookie.
 *
 * The caller must remove the token from the URL immediately afterwards
 * (`history.replaceState`), so it does not survive in browser history.
 */
export async function exchangeBootstrapToken(token: string): Promise<void> {
  const response = await fetch(
    `${API_PREFIX}/bootstrap?token=${encodeURIComponent(token)}`,
    { method: "POST", credentials: "same-origin" },
  );
  if (!response.ok) {
    throw new StudioRequestError(response.status, await readProblem(response));
  }
}
