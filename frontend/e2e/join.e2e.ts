import { expect, INVITED_TEAM, test } from "./fixtures";

test.describe("an invite link", () => {
  test("shows who it is for before anyone signs in, and joins nobody by being opened", async ({
    guest,
    api,
    isMobile,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    api.invites["good-code"] = "active";
    await guest.goto("/join/good-code");
    await expect(guest.getByRole("heading", { name: `Join ${INVITED_TEAM}?` })).toBeVisible();
    await expect(guest.getByText("Made-up Owner invited you to this team.")).toBeVisible();
    const signIn = guest.getByRole("button", { name: "Sign in with Google to join" });
    await expect(signIn).toBeVisible();
    expect((await signIn.boundingBox())!.height).toBeGreaterThanOrEqual(isMobile ? 44 : 40);
    await expectNoHorizontalScroll(guest);
    await expectAccessible(guest);
    expect(api.accepted).toEqual([]);
  });

  test("a signed-in visitor joins with a second, explicit click and lands in the app", async ({
    app,
    api,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    api.invites["good-code"] = "active";
    await app.goto("/join/good-code");
    await expect(app.getByRole("heading", { name: `Join ${INVITED_TEAM}?` })).toBeVisible();
    await expectNoHorizontalScroll(app);
    await expectAccessible(app);
    expect(api.accepted, "opening the link must not join").toEqual([]);

    await app.getByRole("button", { name: "Join team" }).click();
    await expect(app).toHaveURL(/\/$/);
    await expect(app.getByRole("heading", { name: "Lineup", exact: true })).toBeVisible();
    expect(api.accepted).toEqual(["good-code"]);
  });

  test("an expired or revoked link says so", async ({
    guest,
    api,
    expectAccessible,
    expectNoHorizontalScroll,
  }) => {
    api.invites["old-code"] = "gone";
    await guest.goto("/join/old-code");
    await expect(
      guest.getByRole("heading", { name: "This invite link no longer works" }),
    ).toBeVisible();
    await expect(guest.getByRole("link", { name: "Go to the app" })).toBeVisible();
    await expectNoHorizontalScroll(guest);
    await expectAccessible(guest);
  });

  test("an unknown link says so", async ({ guest, expectAccessible, expectNoHorizontalScroll }) => {
    await guest.goto("/join/nope");
    await expect(
      guest.getByRole("heading", { name: "We don't recognise this link" }),
    ).toBeVisible();
    await expectNoHorizontalScroll(guest);
    await expectAccessible(guest);
  });

  test("the Hungarian page passes the accessibility check", async ({
    guest,
    api,
    expectAccessible,
  }) => {
    api.invites["good-code"] = "active";
    await guest.addInitScript(() => localStorage.setItem("lineup-lang", "hu"));
    await guest.goto("/join/good-code");
    await expect(guest.locator("html")).toHaveAttribute("lang", "hu");
    await expect(guest.getByRole("button", { name: /Google/ })).toBeVisible();
    await expectAccessible(guest);
  });
});
