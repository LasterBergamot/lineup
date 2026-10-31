import { expect, test } from "./fixtures";

test("an unknown address shows the 404 page inside the app, which fits the screen and is accessible", async ({
  app,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await app.goto("/no/such/page");
  await expect(app.getByRole("heading", { name: "Page not found" })).toBeVisible();
  await expectNoHorizontalScroll(app);
  await expectAccessible(app);

  await app.getByRole("link", { name: "Back to the lineup" }).click();
  await expect(app).toHaveURL(/\/$/);
  await expect(app.getByRole("heading", { name: "Lineup", exact: true })).toBeVisible();
});

test("a visitor who is not signed in is sent to sign-in, not shown the 404 page", async ({
  guest,
}) => {
  await guest.goto("/no/such/page");
  await expect(guest).toHaveURL(/\/sign-in$/);
  await expect(guest.getByRole("heading", { name: "Page not found" })).toHaveCount(0);
});
