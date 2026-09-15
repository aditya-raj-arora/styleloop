import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

// This CI environment has no OPENWEATHER_API_KEY (see e2e/README.md), so
// the forecast lookup degrades to "no signal" — the real fallback path
// packing.generate_packing_list is built to handle (see docs/TASKS.md's
// Sprint 6 section), not a mock. With no forecast, "bring a layer" always
// shows; that's exercised here for real rather than asserted against a
// specific temperature.
test("generating a packing list for the seeded demo wardrobe", async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
  await page.getByRole("link", { name: "Pack for a trip" }).click();
  await expect(page).toHaveURL(/\/packing/);

  await page.getByRole("button", { name: "Generate" }).click();

  await expect(page.getByText(/\d+ days?/)).toBeVisible();
  await expect(page.getByText("🧥 Bring a layer")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tops" })).toBeVisible();
  await expect(page.getByRole("img").first()).toBeVisible();
});
