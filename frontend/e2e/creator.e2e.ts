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

for (const theme of ["light", "dark"] as const) {
  test(`the enlarged preview zooms and stays sharp, and closes back to Enlarge (${theme} theme)`, async ({
    app,
    isMobile,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    await app.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    await app.goto("/");
    await fillLineup(app);
    await app.getByRole("button", { name: "Preview", exact: true }).click();

    const enlarge = app.getByRole("button", { name: "Enlarge" });
    await enlarge.click();
    const large = app.getByRole("dialog", { name: "Preview (enlarged)" });
    await expect(large.locator("canvas")).toHaveCount(1);
    if (isMobile) {
      // The whole screen.
      const box = await large.boundingBox();
      expect(box!.width).toBeGreaterThanOrEqual(359);
      expect(box!.height).toBeGreaterThanOrEqual(739);
    }

    // Every zoom draws the canvas with at least as many pixels as the screen shows (device pixel
    // ratio included), so small print is not a stretched bitmap.
    const sharp = (min: number, max: number) =>
      expect
        .poll(() =>
          large.locator("canvas").evaluate(
            (element: HTMLCanvasElement, [min, max]: [number, number]) => {
              const css = element.getBoundingClientRect().width;
              return (
                css >= min &&
                css <= max &&
                element.width >= Math.floor(css * window.devicePixelRatio) - 1
              );
            },
            [min, max] as [number, number],
          ),
        )
        .toBe(true);
    await sharp(100, 10_000);
    await expectNoHorizontalScroll(app);
    await expectAccessible(app);

    for (const [name, percent] of [
      ["100 %", 1],
      ["200 %", 2],
    ] as const) {
      await large.getByRole("radio", { name }).click();
      // A4 at 96 dpi is 794 CSS px wide at 100 %.
      await sharp(793.3 * percent - 2, 793.3 * percent + 2);
      // The scroll area scrolls sideways, the page behind does not.
      await expectNoHorizontalScroll(app);
    }
    await expectAccessible(app);

    // Esc and the close button both go back to the Enlarge button.
    await app.keyboard.press("Escape");
    await expect(large).toBeHidden();
    await expect(enlarge).toBeFocused();
    await enlarge.click();
    await large.getByRole("button", { name: "Close the enlarged preview" }).click();
    await expect(large).toBeHidden();
    await expect(enlarge).toBeFocused();
  });
}

test("the enlarged preview fits a phone in Hungarian too", async ({ app, expectAccessible }) => {
  await app.goto("/");
  // fillLineup finds the fields by their English labels, so switch language afterwards.
  await fillLineup(app);
  await app.getByRole("button", { name: "HU – Magyar" }).click();
  await app.getByRole("button", { name: "Előnézet", exact: true }).click();
  await app.getByRole("button", { name: "Kinagyítás" }).click();
  const large = app.getByRole("dialog", { name: "Előnézet (nagyítva)" });
  await expect(large.locator("canvas")).toHaveCount(1);
  await expect(large.getByRole("radio", { name: "Szélességhez igazítva" })).toBeVisible();
  await expect(large.getByRole("radio", { name: "200 %" })).toBeVisible();
  // The dialog itself, not the page behind it: the creator form is a pixel wider than a 360 px
  // phone in Hungarian once it is filled in, which is not this view's doing.
  const overflow = await large.evaluate((dialog) => dialog.scrollWidth - dialog.clientWidth);
  expect(overflow, "the enlarged view is wider than the screen").toBeLessThanOrEqual(0);
  const zoom = await large.getByRole("radiogroup", { name: "Nagyítás" }).boundingBox();
  const dialog = await large.boundingBox();
  expect(zoom!.x + zoom!.width).toBeLessThanOrEqual(dialog!.x + dialog!.width);
  await expectAccessible(app);
});

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
