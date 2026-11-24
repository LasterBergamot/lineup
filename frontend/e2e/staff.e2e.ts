import { expect, test } from "./fixtures";

test("the Staff card adds, defaults and deletes by keyboard, and the creator starts from the default", async ({
  app,
  api,
  expectAccessible,
}) => {
  await app.goto("/roster");
  const card = app.getByRole("form", { name: "Add a staff member" });
  await expect(app.getByRole("region", { name: "Coach" })).toBeVisible();

  // Typed in, by keyboard only: role, name, default, then Enter submits.
  await card.getByLabel("Role", { exact: true }).selectOption("ball_thrower");
  await card.getByLabel("Name", { exact: true }).fill("Thrower Typed");
  await card.getByLabel("Default for this role").check();
  await card.getByLabel("Name", { exact: true }).press("Enter");
  const throwers = app.getByRole("region", { name: "Ball thrower" });
  await expect(throwers.getByText("Thrower Typed")).toBeVisible();
  expect(api.staff.find((s) => s.name === "Thrower Typed")).toMatchObject({
    role: "ball_thrower",
    is_default: true,
    source_player_id: null,
  });

  // Picked from the roster with the arrow keys.
  await card.getByLabel("Role", { exact: true }).selectOption("assistant_coach");
  const picker = card.getByRole("combobox", { name: "Player from the roster" });
  await picker.fill("player 03");
  await picker.press("Enter");
  await expect(card.getByLabel("Name", { exact: true })).toHaveValue("Player 03");
  await card.getByRole("button", { name: "Add staff member" }).click();
  await expect(app.getByRole("region", { name: "Assistant coach" })).toBeVisible();
  expect(api.staff.find((s) => s.role === "assistant_coach")?.source_player_id).toBe("p-3");

  // The second coach becomes the default; the old one loses it.
  await app.getByRole("button", { name: "Make default: Coach Second (Coach)" }).click();
  await expect(
    app.getByRole("button", { name: "Make default: Coach Default (Coach)" }),
  ).toBeVisible();
  await expectAccessible(app);

  // Deleting asks first.
  await app.getByRole("button", { name: "Delete Player 02 (Team leader)" }).click();
  await app.getByRole("button", { name: "Yes, delete" }).click();
  await expect(app.getByRole("region", { name: "Team leader" })).toHaveCount(0);

  await app.getByRole("link", { name: "Lineup" }).first().click();
  const coach = app.getByRole("combobox", { name: "Coach", exact: true }).filter({ visible: true });
  await expect(coach).toHaveValue("Coach Second");
  await expect(
    app.getByRole("combobox", { name: "Ball thrower (optional)" }).filter({ visible: true }),
  ).toHaveValue("Thrower Typed");
  // The role's entries are suggested, the default first; free text stays possible.
  await coach.fill("");
  await coach.press("ArrowDown");
  await expect(app.getByRole("option", { name: "Coach Second" })).toBeVisible();
  await coach.press("ArrowDown");
  await coach.press("Enter");
  await expect(coach).toHaveValue("Coach Default");
  await coach.fill("Coach Carter");
  await expect(coach).toHaveValue("Coach Carter");
  await expectAccessible(app);
});

test("the Staff card passes the accessibility check in Hungarian with an edit form open", async ({
  app,
  expectAccessible,
  expectNoHorizontalScroll,
}) => {
  await app.addInitScript(() => localStorage.setItem("lineup-lang", "hu"));
  await app.goto("/roster");
  await app.getByRole("button", { name: "Szerkesztés: Coach Second (Edző)" }).click();
  await expect(app.getByRole("form", { name: "Szerkesztés: Coach Second (Edző)" })).toBeVisible();
  await expectNoHorizontalScroll(app);
  await expectAccessible(app);
});
