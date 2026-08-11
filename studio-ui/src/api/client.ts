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
