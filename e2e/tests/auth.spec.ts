import { expect, test } from "@playwright/test";

import { login, signup, uniqueEmail } from "../fixtures/auth";

test("signup logs the user in and lands on the dashboard", async ({ page }) => {
  await signup(page, uniqueEmail(), "correct-horse-battery-staple");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/good (morning|afternoon|evening|night)/i);
});

test("a protected route redirects to login when signed out", async ({ page }) => {
  await page.goto("/wardrobe");
  // RequireAuth bounces to "/" (the login page) when there's no token.
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "VogueVault" })).toBeVisible();
});

test("logout clears the session and protects routes again", async ({ page }) => {
  const email = uniqueEmail();
  await signup(page, email, "correct-horse-battery-staple");

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL("/");

  await page.goto("/wardrobe");
  await expect(page).toHaveURL("/");
});

test("a returning user can log back in", async ({ page }) => {
  const email = uniqueEmail();
  const password = "correct-horse-battery-staple";
  await signup(page, email, password);
  await page.getByRole("button", { name: "Log out" }).click();

  await login(page, email, password);
  await expect(page).toHaveURL(/\/dashboard/);
});

test("a wrong password is rejected with a visible error", async ({ page }) => {
  const email = uniqueEmail();
  await signup(page, email, "correct-horse-battery-staple");
  await page.getByRole("button", { name: "Log out" }).click();

  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL("/");
});
