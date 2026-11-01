import { expect, test } from "./fixtures";

test("previewing a saved lineup highlights its row", async ({
  app,
  isMobile,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/saved");
  const row = app.getByRole("listitem").filter({ hasText: "SZVTK - Opponent 2" });
  await app.getByRole("button", { name: "Preview SZVTK - Opponent 2" }).click();
  // A modal dialog on a phone, a side panel on a desktop.
  const panel = isMobile
    ? app.getByRole("dialog", { name: /Opponent 2/ })
    : app.getByRole("complementary", { name: /Opponent 2/ });
  await expect(panel.locator("canvas")).toHaveCount(1);
  await expect(row).toHaveAttribute("aria-current", "true");
  await expect(app.getByRole("listitem").filter({ hasText: "Opponent 1" })).not.toHaveAttribute(
    "aria-current",
  );
  if (isMobile) {
    expect((await panel.boundingBox())!.width).toBeGreaterThanOrEqual(359);
  }
  await expectNoHorizontalScroll(app);
});
