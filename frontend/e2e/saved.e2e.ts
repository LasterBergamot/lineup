import { expect, test } from "./fixtures";

test("previewing a saved lineup highlights its row", async ({
  app,
  isMobile,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/saved");
  const row = app.getByRole("listitem").filter({ hasText: "SZVTK - Opponent 2" });
  await app.getByRole("button", { name: "Preview SZVTK - Opponent 2" }).click();
  const panel = app.getByRole("complementary", { name: /Opponent 2/ });
  await expect(panel.locator("canvas")).toHaveCount(1);
  await expect(row).toHaveAttribute("aria-current", "true");
  await expect(row).toHaveClass(/bg-accent/);
  await expect(app.getByRole("listitem").filter({ hasText: "Opponent 1" })).not.toHaveClass(
    /bg-accent/,
  );
  if (isMobile) {
    expect((await panel.boundingBox())!.width).toBeGreaterThanOrEqual(359);
  }
  await expectNoHorizontalScroll(app);
});
