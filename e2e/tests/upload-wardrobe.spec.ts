import { expect, test } from "@playwright/test";

import { signup, uniqueEmail } from "../fixtures/auth";
import { testImageFile } from "../fixtures/testImage";

// This CI environment has no GEMINI_API_KEY/DEEPAI_API_KEY/rembg configured
// (see e2e/README.md), so the async bg-removal + tagging pipeline never
// actually completes here — the garment stays in its "Processing…" placeholder
// state forever, same as it would for a real user during the few seconds
// before the worker finishes. That's exactly what this test asserts: the
// upload succeeds and the placeholder appears immediately (202 Accepted +
// optimistic UI), which is the frontend behavior this suite owns. The
// pipeline's own correctness (bg-removal, tagging) is covered by the
// backend's test_bg_removal.py/test_tagging.py, not here.
test("uploading a garment shows it in the wardrobe with a processing placeholder", async ({
  page,
}) => {
  await signup(page, uniqueEmail(), "correct-horse-battery-staple");

  await page.getByRole("link", { name: "Upload garment" }).click();
  await expect(page).toHaveURL(/\/upload/);

  await page.getByLabel("Choose a garment photo").setInputFiles(testImageFile());
  await expect(page.getByText("Added — processing in the background.")).toBeVisible();

  await page.getByRole("button", { name: "View in wardrobe →" }).click();
  await expect(page).toHaveURL(/\/wardrobe/);
  await expect(page.getByText("1 item in your closet.")).toBeVisible();
  await expect(page.getByText("Processing…")).toBeVisible();
});
