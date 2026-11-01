import { expect, test } from "./fixtures";

for (const theme of ["light", "dark"] as const) {
  test(`a visitor is sent to the sign-in page, which fits the screen and is accessible (${theme} theme)`, async ({
    guest,
    isMobile,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    await guest.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    await guest.goto("/saved");
    await expect(guest).toHaveURL(/\/sign-in$/);
    await expect(guest.getByRole("heading", { name: "Sign in" })).toBeVisible();
    const google = guest.getByRole("button", { name: "Continue with Google" });
    await expect(google).toBeVisible();
    expect((await google.boundingBox())!.height).toBeGreaterThanOrEqual(isMobile ? 44 : 40);
    await expectNoHorizontalScroll(guest);
    await expectAccessible(guest);
  });
}
