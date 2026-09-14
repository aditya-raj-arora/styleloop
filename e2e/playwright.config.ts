import { defineConfig, devices } from "@playwright/test";

// Both the frontend dev server and the backend API are started as separate
// CI steps (see .github/workflows/e2e.yml) before Playwright runs — not via
// this config's webServer option — because the backend needs a DB migration
// (and, for the seeded-user tests, scripts/seed.py) to run first. Locally,
// see e2e/README.md for the same steps.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // tests share one Postgres DB - no cross-test isolation like the backend's own tests have
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  // The default 5s expect timeout is tight for this suite: every assertion
  // is a real network round-trip (no mocking), on a CI runner running the
  // API + worker + frontend dev server + browser all at once. A more
  // generous default cuts down on resource-contention flakiness across the
  // whole suite rather than bumping individual assertions one at a time.
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
