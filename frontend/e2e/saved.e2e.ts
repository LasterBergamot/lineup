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

test("a saved lineup's preview can be enlarged and closed again", async ({
  app,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/saved");
  await app.getByRole("button", { name: "Preview SZVTK - Opponent 2" }).click();
  const enlarge = app.getByRole("button", { name: "Enlarge" });
  await enlarge.click();
  const large = app.getByRole("dialog", { name: /Opponent 2.*\(enlarged\)/ });
  await expect(large.locator("canvas")).toHaveCount(1);
  await large.getByRole("radio", { name: "150 %" }).click();
  await expectNoHorizontalScroll(app);
  await expectAccessible(app);
  await app.keyboard.press("Escape");
  await expect(large).toBeHidden();
  await expect(enlarge).toBeFocused();
});

test("the saved list shows the side of each lineup, a dash for an old one", async ({ app }) => {
  await app.goto("/saved");
  await expect(app.getByRole("listitem").filter({ hasText: "SZVTK - Opponent 2" })).toContainText(
    "Home/away: Home",
  );
  await expect(app.getByRole("listitem").filter({ hasText: "SZVTK - Opponent 1" })).toContainText(
    "Home/away: –",
  );
});

test("the filter bar narrows the list by opponent, dates and location, and Clear restores it", async ({
  app,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/saved");
  const list = app.getByRole("list", { name: "Saved lineups of SZVTK" });
  await expect(list.getByRole("listitem")).toHaveCount(3);

  await app.getByRole("searchbox", { name: "Opponent" }).fill("opponent 2");
  await expect(list.getByRole("listitem")).toHaveCount(1);
  await expect(list).toContainText("SZVTK - Opponent 2");

  // Filters combine: the opponent matches, but the date range excludes it.
  await app.getByLabel("From date").fill("2026-10-13");
  await expect(app.getByText("No saved lineups match these filters.")).toBeVisible();
  await expectAccessible(app);
  await expectNoHorizontalScroll(app);

  await app.getByRole("button", { name: "Clear filters" }).click();
  await expect(list.getByRole("listitem")).toHaveCount(3);

  await app.getByRole("searchbox", { name: "Location" }).fill("szeged");
  await expect(list.getByRole("listitem")).toHaveCount(1);
  await expect(list).toContainText("Opponent 2");
  await app.getByLabel("To date").fill("2026-10-11");
  await expect(app.getByText("No saved lineups match these filters.")).toBeVisible();
});
