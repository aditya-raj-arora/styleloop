import type { Page } from "@playwright/test";

// scripts/seed.py's demo user — pre-seeded with 10 varied, already-tagged
// 'clean' garments (bypassing the async bg-removal/tagging pipeline, which
// needs external API keys this CI environment doesn't have — see
// e2e/README.md). Used by every spec that needs a wardrobe to already
// exist (outfit generation, swipe, laundry, try-on); the upload/wardrobe
// spec is the only one that goes through real signup instead.
export const DEMO_EMAIL = "demo@styleloop.dev";
export const DEMO_PASSWORD = "demo1234";

export function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

export async function signup(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: /sign up/i }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /sign up/i }).click();
  await page.waitForURL(/\/dashboard/);
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await page.waitForURL(/\/dashboard/);
}
