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

test("fill in a lineup from the roster, preview it and close the preview", async ({
  app,
  api,
  isMobile,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/");
  await app.getByLabel("Opponent", { exact: true }).fill("Opponent X");
  await app.getByLabel("Division").fill("OB I");
  await app.getByLabel("Date").fill("2026. 11. 1.");
  await app.getByLabel("Coach", { exact: true }).fill("Coach Carter");
  await app.getByLabel("Player from the roster").first().selectOption({ label: "Player 01" });
  await expect(app.getByLabel("Name", { exact: true }).first()).toHaveValue("Player 01");

  await app.getByRole("button", { name: "Preview", exact: true }).click();
  const panel = app.getByRole("complementary", { name: /preview/i });
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

  await panel.getByRole("button", { name: "Close the preview" }).click();
  await expect(panel).toBeHidden();
});
