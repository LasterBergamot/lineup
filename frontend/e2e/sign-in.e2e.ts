import { expect, test } from "./fixtures";

test("a visitor is sent to the sign-in page, which fits the screen and is accessible", async ({
  guest,
  isMobile,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await guest.goto("/saved");
  await expect(guest).toHaveURL(/\/sign-in$/);
  await expect(guest.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const google = guest.getByRole("button", { name: "Continue with Google" });
  await expect(google).toBeVisible();
  expect((await google.boundingBox())!.height).toBeGreaterThanOrEqual(isMobile ? 44 : 40);
  await expectNoHorizontalScroll(guest);
  await expectAccessible(guest);
});
