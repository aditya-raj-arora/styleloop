import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

// scripts/seed.py's demo wardrobe has a deliberate wear-count spread (a
// black top worn 8x is the single most-worn garment; a striped top and a
// red dress sit at 0) and at least one clean, tagged garment in every
// essential category, so this exercises "most worn" and "never worn" for
// real without hitting the empty-wardrobe case covered elsewhere.
test("wardrobe analytics panel shows most-worn and never-worn garments", async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
  await page.getByRole("link", { name: "Wardrobe" }).click();
  await expect(page).toHaveURL(/\/wardrobe/);

  const toggle = page.getByRole("button", { name: "Wardrobe analytics ▼" });
  await expect(toggle).toBeVisible();
  await toggle.click();

  await expect(page.getByRole("button", { name: "Hide analytics ▲" })).toBeVisible();
  await expect(page.getByText("Most worn")).toBeVisible();
  await expect(page.getByText("8× worn")).toBeVisible();
  await expect(page.getByText("Never worn")).toBeVisible();

  // The demo wardrobe covers every essential category, so there's nothing
  // to flag as a gap.
  await expect(page.getByText(/^No (top|bottom|dress|outerwear|shoes)$/)).toHaveCount(0);

  await page.getByRole("button", { name: "Hide analytics ▲" }).click();
  await expect(page.getByText("Most worn")).toHaveCount(0);
});
