/**
 * A controllable `EventSource` for tests.
 *
 * jsdom has no `EventSource` at all, so a component that opens a stream either throws
 * `EventSource is not defined` or gets a stub so permissive that reconnect and
 * `Last-Event-ID` are never exercised. This fake exists to make those two behaviours
 * ASSERTABLE rather than assumed:
 *
 * * `emit` delivers one frame, recording the id the way a real browser does, so the
 *   value a reconnect would send is observable rather than inferred;
 * * `close`/`fail` simulate the connection ending, which is the NORMAL path for Studio's
 *   finite-replay endpoint -- the server serves what it has and closes, and the browser
 *   reconnects with `Last-Event-ID`.
 *
 * It deliberately does NOT reconnect on its own. A fake that reconnected on a timer
 * would make tests depend on wall-clock timing; instead a test asks for the next
 * connection explicitly and inspects what it carried.
 */

export interface FakeConnection {
  /** The URL this connection was opened with. */
  readonly url: string;
  /** The `Last-Event-ID` a real browser would have sent, or `null` on first connect. */
  readonly lastEventId: string | null;
  /** Whether this connection has been closed (by the page or the server). */
  readonly closed: boolean;
}

type Listener = (event: MessageEvent) => void;

/**
 * The registry of connections a test can inspect.
 *
 * A module-level registry rather than an injected factory: `EventSource` is looked up on
 * `window` by the code under test, so intercepting it there is what actually proves the
 * component would work in a browser.
 */
export class FakeEventSourceRegistry {
  connections: FakeEventSource[] = [];
  /** Persisted across connections, exactly as a browser persists it. */
  lastSeenId: string | null = null;

  /** The most recent connection, or `undefined` before the first one. */
  get current(): FakeEventSource | undefined {
    return this.connections[this.connections.length - 1];
  }

  reset(): void {
    this.connections = [];
    this.lastSeenId = null;
  }
}

export class FakeEventSource implements FakeConnection {
  static registry = new FakeEventSourceRegistry();

  readonly url: string;
  readonly lastEventId: string | null;
  closed = false;
  onerror: ((event: Event) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;

  private listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    // A browser sends the id it last saw, not one the page supplies.
    this.lastEventId = FakeEventSource.registry.lastSeenId;
    FakeEventSource.registry.connections.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const existing = this.listeners.get(type) ?? [];
    this.listeners.set(type, [...existing, listener]);
  }

  removeEventListener(type: string, listener: Listener): void {
    const existing = this.listeners.get(type) ?? [];
    this.listeners.set(
      type,
      existing.filter((candidate) => candidate !== listener),
    );
  }

  close(): void {
    this.closed = true;
  }

  /** Deliver one frame, recording its id the way a browser would. */
  emit(type: string, data: unknown, id?: string): void {
    if (id !== undefined) {
      FakeEventSource.registry.lastSeenId = id;
    }
    const event = new MessageEvent(type, {
      data: JSON.stringify(data),
      lastEventId: id ?? "",
    });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  /** Simulate the server closing the response, which is Studio's normal path. */
  fail(): void {
    this.closed = true;
    this.onerror?.(new Event("error"));
  }
}

/** Install the fake, returning its registry and an uninstall function. */
export function installFakeEventSource(): {
  registry: FakeEventSourceRegistry;
  uninstall: () => void;
} {
  const original = (globalThis as Record<string, unknown>).EventSource;
  FakeEventSource.registry.reset();
  (globalThis as Record<string, unknown>).EventSource = FakeEventSource;
  return {
    registry: FakeEventSource.registry,
    uninstall: () => {
      (globalThis as Record<string, unknown>).EventSource = original;
    },
  };
}
