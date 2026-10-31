import { expect, test } from "./fixtures";

// The phone project only: these are the things that make a page awkward under a thumb.
test.beforeEach(({ isMobile }) => {
  test.skip(!isMobile, "touch behaviour");
});

test("text fields are 16 px, so iOS does not zoom the page when one is focused", async ({
  app,
}) => {
  await app.goto("/");
  await expect(app.getByLabel("Division")).toBeVisible();
  const sizes = await app
    .locator("input:not([type=checkbox]), select")
    .evaluateAll((els) => els.map((el) => parseFloat(getComputedStyle(el).fontSize)));
  expect(sizes.length).toBeGreaterThan(0);
  expect(Math.min(...sizes)).toBeGreaterThanOrEqual(16);
});

test("every button, link and field is at least 44 px tall", async ({ app }) => {
  for (const path of ["/", "/saved", "/members", "/roster"]) {
    await app.goto(path);
    await expect(app.getByRole("main")).toBeVisible();
    const small = await app
      .locator("button:visible, a:visible, input:not([type=checkbox]):visible, select:visible")
      .evaluateAll((els) =>
        els
          .map((el) => ({
            name: el.getAttribute("aria-label") ?? el.textContent,
            h: el.getBoundingClientRect().height,
          }))
          .filter(({ h }) => h < 44),
      );
    expect(small, `small tap targets on ${path}`).toEqual([]);
  }
});
