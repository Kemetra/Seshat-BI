/**
 * Browser entry point.
 *
 * Performs the one-time bootstrap exchange when the launch URL carries a token, then
 * strips it from history immediately -- the contract requires the token to live in the
 * URL "only long enough to perform POST /api/v1/bootstrap", so leaving it in the
 * address bar or the back stack would violate that. See `bootstrap.ts`.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { consumeBootstrapToken } from "./bootstrap";
import "./tokens.css";

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
