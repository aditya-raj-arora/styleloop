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
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
