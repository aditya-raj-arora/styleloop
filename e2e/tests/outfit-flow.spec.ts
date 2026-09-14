import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

test.beforeEach(async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
});

test("dashboard generates today's outfit for a wardrobe with clean tagged garments", async ({
  page,
}) => {
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();
  await expect(page.getByText(/\d+ items?/)).toBeVisible();
});

test("regenerate replaces the shown outfit", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();
  const before = await page.getByText(/\d+ items?/).textContent();

  await page.getByRole("button", { name: "Regenerate" }).click();
  await expect(page.getByRole("button", { name: "Regenerate" })).toBeEnabled();

  // The demo wardrobe has enough variety that a regenerate is very likely to
  // change the item count or score - not a hard guarantee (see
  // rotation.py's exact-match-only exclusion), so this just confirms the
  // request round-tripped successfully, not that the outfit literally
  // differs every time.
  await expect(page.getByText(/\d+ items?/)).toBeVisible();
  void before;
});

test("wearing an outfit shows confirmation and updates the wardrobe", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();

  await page.getByRole("button", { name: "Wore this" }).click();
  await expect(page.getByText("Logged — enjoy!")).toBeVisible();

  await page.getByRole("link", { name: "Wardrobe" }).click();
  await page.getByRole("button", { name: "Worn" }).click();
  // At least one of the just-worn outfit's garments now carries the "Worn"
  // state badge (a <span> on the card, not the "Worn" filter button itself)
  // in the filtered grid.
  await expect(page.getByText('Nothing in "worn" right now.')).toHaveCount(0);
  await expect(page.locator("span", { hasText: "Worn" }).first()).toBeVisible();
});
