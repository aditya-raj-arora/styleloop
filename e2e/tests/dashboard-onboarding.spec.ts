import { expect, test } from "@playwright/test";

import { signup, uniqueEmail } from "../fixtures/auth";

// A brand new signup has no garments yet, so GET /outfits/daily 422s and
// the Dashboard falls back to the first-run checklist instead of the demo
// user's real outfit (covered by outfit-flow.spec.ts). Doesn't go through
// the upload pipeline (no API keys in this CI environment — see
// upload-wardrobe.spec.ts) since the point here is the checklist's initial
// state, not a step actually completing.
test("a fresh signup sees the onboarding checklist instead of a bare error", async ({ page }) => {
  await signup(page, uniqueEmail(), "correct-horse-battery-staple");

  await expect(page.getByRole("heading", { name: "Let's get you set up" })).toBeVisible();
  await expect(page.getByText("Upload a few garments")).toBeVisible();
  await expect(page.getByRole("link", { name: "Upload garments →" })).toBeVisible();

  // Nothing is done yet.
  await expect(page.getByText("Have a top + bottom, or a dress")).toBeVisible();
  await expect(page.getByText("Add a photo of yourself (optional)")).toBeVisible();

  await page.getByRole("link", { name: "Upload garments →" }).click();
  await expect(page).toHaveURL(/\/upload/);
});
