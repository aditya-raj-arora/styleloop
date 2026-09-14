import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";
import { testImageFile } from "../fixtures/testImage";

// FASHN_API_KEY isn't configured in this CI environment (a real render
// costs money and needs a live account - see e2e/README.md), so
// services/tryon.render_tryon fails immediately and no cached render ever
// appears. That's an intentional exercise of the real degrade-gracefully
// path this feature was built with (see docs/rotation-scoring-design-note.md's
// Sprint 4 section) - this test verifies the request round-trips into the
// "pending" state, not that a render completes.
test("uploading a base photo enables try-on and starts a render", async ({ page }) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);

  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();
  await page.getByLabel("Choose a photo of yourself for virtual try-on").setInputFiles(
    testImageFile("me.png"),
  );
  await expect(page.getByText("📷 Try-on photo saved.")).toBeVisible();

  await page.getByRole("button", { name: "Try it on" }).click();
  await expect(page.getByText("Rendering on your photo…")).toBeVisible();
});
