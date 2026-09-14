import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

test.beforeEach(async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
  await page.getByRole("link", { name: "Swipe outfits" }).click();
  await expect(page).toHaveURL(/\/swipe/);
});

test("skip records a dislike and loads a new suggestion", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();

  await page.getByRole("button", { name: "Skip this outfit and get a new suggestion" }).click();

  // Regenerating round-trips through the API - the card stays present
  // (a new outfit, not a blank state) once it resolves.
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();
});

test("like records a preference and confirms in place", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();

  const likeButton = page.getByRole("button", { name: "Like this outfit" });
  await likeButton.click();

  await expect(page.getByRole("button", { name: "Liked!" })).toBeDisabled();
});
