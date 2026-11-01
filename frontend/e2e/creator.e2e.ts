import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

test("the player row keeps the roster picker wide enough to read on a phone", async ({
  app,
  isMobile,
}) => {
  await app.goto("/");
  const picker = app.getByLabel("Player from the roster").first();
  const name = app.getByLabel("Name", { exact: true }).first();
  const [pickerBox, nameBox] = [await picker.boundingBox(), await name.boundingBox()];
  if (isMobile) {
    // Stacked: the picker is as wide as the name field instead of squeezed beside the cap number.
    expect(pickerBox!.width).toBeGreaterThanOrEqual(nameBox!.width - 1);
  }
  expect(pickerBox!.width).toBeGreaterThan(150);
});

for (const theme of ["light", "dark"] as const) {
  test(`fill in a lineup from the roster, preview it and close the preview (${theme} theme)`, async ({
    app,
    api,
    isMobile,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    await app.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    await app.goto("/");
    await fillLineup(app);

    const preview = app.getByRole("button", { name: "Preview", exact: true });
    await preview.click();
    // A modal dialog on a phone, a side panel on a desktop.
    const panel = isMobile
      ? app.getByRole("dialog", { name: /preview/i })
      : app.getByRole("complementary", { name: /preview/i });
    await expect(panel.locator("canvas")).toHaveCount(1);
    expect(api.previews).toHaveLength(1);

    if (isMobile) {
      // A full-screen sheet: it covers the viewport and the page behind does not scroll sideways.
      const box = await panel.boundingBox();
      expect(box!.width).toBeGreaterThanOrEqual(359);
      expect(box!.height).toBeGreaterThanOrEqual(739);
    }
    await expectNoHorizontalScroll(app);
    await expectAccessible(app);

    if (isMobile) {
      // Esc closes the dialog and focus goes back to the button that opened it.
      await app.keyboard.press("Escape");
      await expect(panel).toBeHidden();
      await expect(preview).toBeFocused();
      // The close button too (the dialog is unmounted by its owner, not closed natively).
      await preview.click();
      await panel.getByRole("button", { name: "Close the preview" }).click();
      await expect(panel).toBeHidden();
      await expect(preview).toBeFocused();
    } else {
      await panel.getByRole("button", { name: "Close the preview" }).click();
      await expect(panel).toBeHidden();
    }
  });
}

test("saving shows a toast that can be dismissed and passes the accessibility check", async ({
  app,
  api,
  expectAccessible,
}) => {
  await app.goto("/");
  await fillLineup(app);
  await app.getByRole("button", { name: "Save lineup" }).click();
  const toast = app.getByRole("region", { name: "Notifications" }).getByText("Lineup saved");
  await expect(toast).toBeVisible();
  expect(api.saved).toHaveLength(4);
  await expectAccessible(app);
  await app.getByRole("button", { name: "Dismiss" }).click();
  await expect(toast).toBeHidden();
});

/** Fills the match details and picks the first roster player. */
async function fillLineup(app: Page) {
  await app.getByLabel("Opponent", { exact: true }).fill("Opponent X");
  await app.getByLabel("Division").fill("OB I");
  await app.getByLabel("Date").fill("2026. 11. 1.");
  await app.getByLabel("Coach", { exact: true }).fill("Coach Carter");
  await app.getByLabel("Player from the roster").first().selectOption({ label: "Player 01" });
  await expect(app.getByLabel("Name", { exact: true }).first()).toHaveValue("Player 01");
}
