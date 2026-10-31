import { expect, test } from "./fixtures";

/** The four signed-in areas, as the nav links name them. */
const SCREENS = [
  { path: "/", heading: /lineup/i },
  { path: "/roster", heading: /roster/i },
  { path: "/saved", heading: /saved/i },
  { path: "/members", heading: /team/i },
] as const;

for (const theme of ["light", "dark"] as const) {
  test.describe(`${theme} theme`, () => {
    test.beforeEach(async ({ app }) => {
      await app.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    });

    for (const { path, heading } of SCREENS) {
      test(`${path} fits the screen and passes the accessibility check`, async ({
        app,
        expectAccessible,
        expectNoHorizontalScroll,
      }) => {
        await app.goto(path);
        await expect(app.getByRole("heading", { name: heading }).first()).toBeVisible();
        await expect(app.getByRole("status", { name: "Loading" })).toHaveCount(0);
        await expectNoHorizontalScroll(app);
        await expectAccessible(app);
      });
    }
  });
}

test("the navigation is reachable and every item is tall enough to tap", async ({
  app,
  isMobile,
}) => {
  await app.goto("/");
  const nav = app.getByRole("navigation", { name: isMobile ? "Bottom" : "Sidebar" });
  await expect(nav).toBeVisible();
  const links = nav.getByRole("link");
  await expect(links).toHaveCount(4);
  for (const link of await links.all()) {
    const box = await link.boundingBox();
    // 44 px is the touch guideline; the desktop sidebar is for a pointer.
    expect(box!.height, "a nav item is tall enough").toBeGreaterThanOrEqual(isMobile ? 44 : 32);
  }
  await nav.getByRole("link", { name: "Saved" }).click();
  await expect(app).toHaveURL(/\/saved$/);
});

test("the other navigation is hidden", async ({ app, isMobile }) => {
  await app.goto("/");
  await expect(app.getByRole("navigation", { name: isMobile ? "Sidebar" : "Bottom" })).toBeHidden();
});

test("the app can be installed: the manifest and its icons are served", async ({ guest }) => {
  await guest.goto("/sign-in");
  const href = await guest.locator('link[rel="manifest"]').getAttribute("href");
  const response = await guest.request.get(href!);
  expect(response.ok()).toBe(true);
  const manifest = (await response.json()) as { icons: { src: string }[] };
  for (const icon of manifest.icons) {
    const file = await guest.request.get(icon.src);
    expect(file.headers()["content-type"], icon.src).toContain("image/png");
  }
});
