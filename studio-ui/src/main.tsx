/**
 * Browser entry point.
 *
 * Performs the one-time bootstrap exchange when the launch URL carries a token, then
 * strips it from history immediately -- the contract requires the token to live in the
 * URL "only long enough to perform POST /api/v1/bootstrap", so leaving it in the
 * address bar or the back stack would violate that.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { exchangeBootstrapToken } from "./api/client";
import "./tokens.css";

/** Exchange and erase the token, if this load carries one. */
async function consumeBootstrapToken(): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token === null) return;

  try {
    await exchangeBootstrapToken(token);
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

async function start(): Promise<void> {
  await consumeBootstrapToken();
  const container = document.getElementById("root");
  if (container === null) throw new Error("Studio root element is missing");
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void start();
