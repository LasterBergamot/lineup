import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";

/** Opens "Edit" on the Saved page for the lineup against `Opponent 2` (the fixture's `s-2`). */
async function openEdit(app: Page) {
  await app.goto("/saved");
  await app.getByRole("button", { name: "Edit SZVTK - Opponent 2" }).click();
  await expect(app.getByRole("heading", { name: "Editing SZVTK - Opponent 2" })).toBeVisible();
}

test("edit a saved lineup in place: same id, new values in the list", async ({
  app,
  api,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await openEdit(app);
  // Only the creator: the Quick sheet is not offered while editing.
  await expect(app.getByRole("tab")).toHaveCount(0);
  const division = app.getByLabel("Division");
  await expect(division).toHaveValue("OB I");
  await expect(app.getByLabel("Date")).toHaveValue("2026-10-12");
  await expectNoHorizontalScroll(app);
  await expectAccessible(app);

  await division.fill("OB I/B");
  await app.getByRole("button", { name: "Save changes" }).click();
  await expect(app.getByText("Changes saved")).toBeVisible();

  expect(api.saved).toHaveLength(3);
  const edited = api.saved.find((s) => s.id === "s-2")!;
  expect(edited.division).toBe("OB I/B");
  expect(edited.updated_at).not.toBe(edited.created_at);

  // The toast sits over the bottom of the form on a phone.
  await app.getByRole("button", { name: "Dismiss" }).click();
  // Clean again, so Cancel leaves without asking.
  await app.getByRole("button", { name: "Cancel" }).click();
  const row = app.getByRole("listitem").filter({ hasText: "SZVTK - Opponent 2" });
  await expect(row).toContainText("OB I/B");
  await expect(row).toContainText(/Edited /);
});

test("a concurrent edit gets 409: nothing is overwritten and the latest version can be loaded", async ({
  app,
  api,
}) => {
  await openEdit(app);
  // Another member saves the same lineup meanwhile.
  const theirs = api.saved.find((s) => s.id === "s-2")!;
  Object.assign(theirs, { division: "OB II", updated_at: "2026-11-01T08:00:00Z" });

  await app.getByLabel("Division").fill("Mine");
  await app.getByRole("button", { name: "Save changes" }).click();
  const alert = app.getByRole("alert").filter({ hasText: "Someone else changed this lineup" });
  await expect(alert).toBeVisible();
  expect(api.saved.find((s) => s.id === "s-2")!.division).toBe("OB II");
  await expect(app.getByLabel("Division")).toHaveValue("Mine");

  await alert.getByRole("button", { name: /Load the latest version/ }).click();
  await expect(app.getByLabel("Division")).toHaveValue("OB II");
  await app.getByLabel("Division").fill("OB II/A");
  await app.getByRole("button", { name: "Save changes" }).click();
  await expect(app.getByText("Changes saved")).toBeVisible();
  expect(api.saved.find((s) => s.id === "s-2")!.division).toBe("OB II/A");
});

test("leaving an edit with unsaved changes asks first", async ({ app }) => {
  await openEdit(app);
  await app.getByLabel("Division").fill("Changed");
  await app.getByRole("button", { name: "Cancel" }).click();
  const dialog = app.getByRole("dialog", { name: "Discard changes?" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Discard" }).click();
  await expect(app.getByRole("heading", { name: "Saved lineups" })).toBeVisible();
});

test("editing a lineup another member deleted says so", async ({ app, api }) => {
  await openEdit(app);
  api.saved = api.saved.filter((s) => s.id !== "s-2");
  await app.getByLabel("Division").fill("Changed");
  await app.getByRole("button", { name: "Save changes" }).click();
  await expect(
    app.getByRole("alert").filter({ hasText: /no longer exists; another member/ }),
  ).toBeVisible();
});
