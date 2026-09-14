import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

test("sending a garment to laundry and bulk-resetting it back to clean", async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
  await page.getByRole("link", { name: "Wardrobe" }).click();
  await expect(page).toHaveURL(/\/wardrobe/);

  const toLaundryButtons = page.getByRole("button", { name: /^Send .* to laundry$/ });
  // Wait for the (async) garment fetch to actually render before counting -
  // .count() is a snapshot, not an auto-retrying assertion, so calling it
  // immediately after navigation races the GET /garments request.
  await expect(toLaundryButtons.first()).toBeVisible();
  const before = await toLaundryButtons.count();
  expect(before).toBeGreaterThan(0);

  await toLaundryButtons.first().click();
  // One fewer "send to laundry" button - that garment moved to 'laundry'
  // state and lost the action (GarmentCard only shows it for
  // state !== 'laundry').
  await expect(toLaundryButtons).toHaveCount(before - 1);

  const doLaundry = page.getByRole("button", { name: /^Do Laundry \(\d+\)$/ });
  await expect(doLaundry).toBeVisible();
  await doLaundry.click();

  // The bulk button disappears once nothing is left in laundry - it only
  // renders when laundryCount > 0 (Wardrobe.tsx).
  await expect(page.getByRole("button", { name: /^Do Laundry/ })).toHaveCount(0);
  // ...and the garment count back to what it was before this test sent one.
  await expect(toLaundryButtons).toHaveCount(before);
});
