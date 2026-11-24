import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

/** Types into the creator so it holds unsaved changes. */
async function makeDirty(app: Page) {
  await app.getByLabel("Division").filter({ visible: true }).fill("OB I");
  await expect(app.getByLabel("Division").filter({ visible: true })).toHaveValue("OB I");
}

const nav = (app: Page, isMobile: boolean) =>
  app.getByRole("navigation", { name: isMobile ? "Bottom" : "Sidebar" });

for (const theme of ["light", "dark"] as const) {
  test(`leaving the creator with unsaved changes asks first, and the dialog is accessible (${theme} theme)`, async ({
    app,
    isMobile,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    await app.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    await app.goto("/");
    await makeDirty(app);

    await nav(app, isMobile).getByRole("link", { name: "Roster" }).click();
    const dialog = app.getByRole("dialog", { name: "Discard changes?" });
    await expect(dialog).toBeVisible();
    await expectNoHorizontalScroll(app);
    await expectAccessible(app);

    // Stay (Esc means the same): the form keeps what was typed.
    await app.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(app).toHaveURL(/\/$/);
    await expect(app.getByLabel("Division").filter({ visible: true })).toHaveValue("OB I");

    await nav(app, isMobile).getByRole("link", { name: "Roster" }).click();
    await dialog.getByRole("button", { name: "Discard" }).click();
    await expect(app).toHaveURL(/\/roster$/);
    await expect(dialog).toBeHidden();
  });
}

test("the browser asks before closing the tab while the creator is dirty, not after saving", async ({
  app,
  isMobile,
}) => {
  await app.goto("/");
  await makeDirty(app);
  const asked = app.waitForEvent("dialog");
  await app.close({ runBeforeUnload: true }).catch(() => {});
  const prompt = await asked;
  expect(prompt.type()).toBe("beforeunload");
  await prompt.dismiss();
  await expect(app.getByLabel("Division").filter({ visible: true })).toHaveValue("OB I");

  // Filled in and saved: nothing to lose, so the navigation goes straight through.
  await app.getByLabel("Opponent", { exact: true }).filter({ visible: true }).fill("Opponent X");
  await app.getByLabel("Date").filter({ visible: true }).fill("2026. 11. 1.");
  await app.getByLabel("Coach", { exact: true }).filter({ visible: true }).fill("Coach Carter");
  await app.getByLabel("Player from the roster").first().selectOption({ label: "Player 01" });
  await app.getByRole("button", { name: "Save lineup" }).click();
  await expect(app.getByRole("region", { name: "Notifications" })).toContainText("Lineup saved");
  await nav(app, isMobile).getByRole("link", { name: "Saved" }).click();
  await expect(app).toHaveURL(/\/saved$/);
  await expect(app.getByRole("dialog", { name: "Discard changes?" })).toHaveCount(0);

  // And the tab closes without the browser asking.
  let promptedAgain = false;
  app.on("dialog", (again) => {
    promptedAgain = true;
    void again.dismiss();
  });
  const closed = app.waitForEvent("close");
  await app.close({ runBeforeUnload: true });
  await closed;
  expect(promptedAgain).toBe(false);
});
