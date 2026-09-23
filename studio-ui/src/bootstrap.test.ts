import { afterEach, describe, expect, it, vi } from "vitest";

import { consumeBootstrapToken } from "./bootstrap";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("consumeBootstrapToken", () => {
  it("resolves, and erases the token, when the exchange is refused", async () => {
    // A spent token (the link clicked twice, or a reload that kept ?token=) answers
    // 401. The browser may still hold a valid session, so start-up must continue to
    // render the App instead of leaving a blank page.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 401 })),
    );
    window.history.replaceState(null, "", "/?token=spent&keep=1");

    await expect(consumeBootstrapToken()).resolves.toBeUndefined();

    expect(window.location.search).toBe("?keep=1");
  });

  it("does nothing when the URL carries no token", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    await consumeBootstrapToken();

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
