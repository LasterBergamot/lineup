import { expect, test } from "./fixtures";

for (const theme of ["light", "dark"] as const) {
  test(`a user without a team creates one and lands in the app (${theme} theme)`, async ({
    app,
    api,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    await app.addInitScript((value) => localStorage.setItem("lineup-theme", value), theme);
    api.teams.length = 0;
    await app.goto("/");
    await expect(app.getByRole("heading", { name: "Welcome to Lineup" })).toBeVisible();
    await expectNoHorizontalScroll(app);
    await expectAccessible(app);

    await app.getByPlaceholder("e.g. SZVTK").fill("Vasas");
    await app.getByRole("button", { name: "Create team" }).click();
    await expect(app.getByRole("heading", { name: "Lineup", exact: true })).toBeVisible();
    expect(api.teams.map((t) => t.name)).toEqual(["Vasas"]);
  });
}
