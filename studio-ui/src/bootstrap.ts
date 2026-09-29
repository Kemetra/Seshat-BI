/**
 * The one-time bootstrap exchange, split from `main.tsx` so it is testable.
 *
 * The contract requires the token to live in the URL "only long enough to perform
 * POST /api/v1/bootstrap", so it is erased from history whether or not the exchange
 * succeeds.
 */

import { exchangeBootstrapToken } from "./api/client";

/** Exchange and erase the token, if this load carries one. */
export async function consumeBootstrapToken(): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token === null) return;

  try {
    await exchangeBootstrapToken(token);
  } catch {
    // A refused exchange -- a spent token from a second click or a reload that kept
    // `?token=` -- must not stop the App rendering: this browser may already hold a
    // valid session, and if it does not, the App's own first request shows the 401
    // problem. Rejecting here left a blank page with no error at all.
  } finally {
    // `finally`, not `then`: a failed exchange must still erase the token. Leaving a
    // burnt or rejected token in history helps nobody and keeps secret-shaped
    // material on screen.
    params.delete("token");
    const query = params.toString();
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${query.length > 0 ? `?${query}` : ""}`,
    );
  }
}
