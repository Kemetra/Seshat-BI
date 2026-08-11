/**
 * Vitest setup. Adds jest-dom's accessibility-aware matchers and clears any stubbed
 * `fetch` between tests, so one test's canned response cannot leak into the next.
 */

import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
