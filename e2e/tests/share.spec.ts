import { expect, test } from "@playwright/test";

import { DEMO_EMAIL, DEMO_PASSWORD, login } from "../fixtures/auth";

test("sharing today's outfit produces a public link, viewable without logging in", async ({
  page,
  context,
}) => {
  await login(page, DEMO_EMAIL, DEMO_PASSWORD);
  await expect(page.getByRole("heading", { name: "Today's Outfit" })).toBeVisible();

  await page.getByRole("button", { name: "Share" }).click();

  const linkInput = page.getByLabel("Shareable outfit link");
  await expect(linkInput).toBeVisible();
  const shareUrl = await linkInput.inputValue();
  expect(shareUrl).toMatch(/\/shared\/[\w-]+$/);

  // Clicking Share again while already shared re-shows the same link rather
  // than a second "Share" button.
  await expect(page.getByRole("button", { name: "Share" })).toHaveCount(0);

  // Open the link in a fresh, unauthenticated browser context - proves the
  // page needs no login, not just that this logged-in tab can still see it.
  const token = new URL(shareUrl).pathname.replace("/shared/", "");
  const publicContext = await context.browser()!.newContext();
  const publicPage = await publicContext.newPage();
  await publicPage.goto(`/shared/${token}`);

  await expect(publicPage.getByRole("heading", { name: "Shared Outfit" })).toBeVisible();
  await expect(publicPage.getByRole("img").first()).toBeVisible();
  await publicContext.close();

  // Revoking it 404s the same link.
  await page.getByRole("button", { name: "Stop sharing" }).click();
  await expect(page.getByRole("button", { name: "Share" })).toBeVisible();

  const revokedPage = await context.browser()!.newPage();
  await revokedPage.goto(`/shared/${token}`);
  await expect(revokedPage.getByText("Link not found")).toBeVisible();
  await revokedPage.close();
});
