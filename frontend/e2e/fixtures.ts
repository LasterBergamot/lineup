import AxeBuilder from "@axe-core/playwright";
import { expect, test as base, type Page, type Route } from "@playwright/test";

/** The fake Supabase project the bundle is built against (see `playwright.config.ts`). */
const SUPABASE_ORIGIN = "http://127.0.0.1:54399";
/** supabase-js keeps the session under `sb-<first label of the host>-auth-token`. */
const SESSION_KEY = "sb-127-auth-token";
const USER_ID = "5a0c0001-0000-4000-8000-000000000001";
const NOW = "2026-10-31T12:00:00Z";

export interface Team {
  id: string;
  name: string;
  created_by: string;
  is_public: boolean;
  created_at: string;
  role: "owner" | "member";
}

interface Player {
  id: string;
  name: string;
  nssz_number: string;
  team_id: string;
  created_at: string;
}

interface Saved {
  id: string;
  team_id: string;
  team_name: string;
  opponent_name: string;
  match_name: string;
  division: string;
  cap: string;
  date: string;
  coach: string;
  doctor: string | null;
  assistant_coach: string | null;
  team_leader: string | null;
  ball_thrower: string | null;
  source_team_id: string | null;
  source_opponent_id: string | null;
  players: { cap_number: number; name: string; nssz_number: string }[];
  created_at: string;
}

/** What the fake backend holds; tests read it to check what the app sent. */
export interface FakeApi {
  teams: Team[];
  players: Player[];
  saved: Saved[];
  /** Every `POST /lineups` body, so a test can check what the preview was asked to render. */
  previews: unknown[];
  /** Requests nobody handled; a test fails when this is not empty. */
  unhandled: string[];
}

/** One-page PDF, enough for pdf.js to draw a canvas. */
const PDF = Buffer.from(
  [
    "%PDF-1.4",
    "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
    "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
    "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj",
    "4 0 obj<</Length 44>>stream",
    "BT /F1 24 Tf 72 700 Td (Lineup) Tj ET",
    "endstream endobj",
    "5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
    "trailer<</Root 1 0 R/Size 6>>",
    "%%EOF",
  ].join("\n"),
);

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

const page_ = <T>(items: T[]) => ({ items, total: items.length, limit: 200, offset: 0 });

export const team = (name: string, role: Team["role"] = "owner"): Team => ({
  id: `t-${name}`,
  name,
  created_by: USER_ID,
  is_public: true,
  created_at: NOW,
  role,
});

/** Fifteen made-up players, enough to fill a lineup. */
export const makePlayers = (teamId: string): Player[] =>
  Array.from({ length: 15 }, (_, i) => ({
    id: `p-${i + 1}`,
    name: `Player ${String(i + 1).padStart(2, "0")}`,
    nssz_number: `NSSZ-${1000 + i}`,
    team_id: teamId,
    created_at: NOW,
  }));

export const makeSaved = (t: Team, i: number): Saved => ({
  id: `s-${i}`,
  team_id: t.id,
  team_name: t.name,
  opponent_name: `Opponent ${i}`,
  match_name: `${t.name} - Opponent ${i}`,
  division: "OB I",
  cap: "Fehér",
  date: `2026. 10. ${10 + i}.`,
  coach: "Coach",
  doctor: null,
  assistant_coach: null,
  team_leader: null,
  ball_thrower: null,
  source_team_id: null,
  source_opponent_id: null,
  players: [{ cap_number: 1, name: "Player 01", nssz_number: "NSSZ-1000" }],
  created_at: NOW,
});

/**
 * Signs the page in (a session in localStorage that supabase-js accepts without a network call)
 * and answers every request to the API and to the fake Supabase host from `api`.
 */
async function install(page: Page, api: FakeApi, signedIn: boolean) {
  // The app is Hungarian unless told otherwise; the tests read English labels.
  await page.addInitScript(() => localStorage.setItem("lineup-lang", "en"));
  if (signedIn) {
    await page.addInitScript(
      ([key, userId]) => {
        const expiresAt = Math.floor(Date.now() / 1000) + 3600;
        localStorage.setItem(
          key!,
          JSON.stringify({
            access_token: "e2e-token",
            refresh_token: "e2e-refresh",
            token_type: "bearer",
            expires_in: 3600,
            expires_at: expiresAt,
            user: { id: userId, aud: "authenticated" },
          }),
        );
      },
      [SESSION_KEY, USER_ID],
    );
  }
  await page.route(`${SUPABASE_ORIGIN}/**`, (route) => json(route, {}));
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname.slice("/api".length);
      const method = request.method();
      const teamId = url.searchParams.get("team_id");

      if (method === "GET" && path === "/health") return json(route, { status: "ok" });
      if (method === "GET" && path === "/teams") return json(route, page_(api.teams));
      if (method === "POST" && path === "/teams") {
        const body = request.postDataJSON() as { name: string; is_public: boolean };
        const created = { ...team(body.name), is_public: body.is_public };
        api.teams.push(created);
        return json(route, created, 201);
      }
      if (method === "GET" && path === "/players") {
        return json(route, page_(api.players.filter((p) => p.team_id === teamId)));
      }
      if (method === "GET" && path === "/lineups/saved") {
        return json(route, page_(api.saved.filter((s) => s.team_id === teamId)));
      }
      if (method === "GET" && path === "/teams/pool") return json(route, []);
      if (method === "GET" && /^\/teams\/[^/]+\/opponents\/recent$/.test(path)) {
        return json(route, ["Opponent 1"]);
      }
      if (method === "GET" && /^\/teams\/[^/]+\/members$/.test(path)) {
        return json(route, [
          { user_id: USER_ID, role: "owner", joined_at: NOW, is_you: true },
          { user_id: "u-2", role: "member", joined_at: NOW, is_you: false },
        ]);
      }
      if (method === "GET" && /^\/teams\/[^/]+\/invitations$/.test(path)) return json(route, []);
      if (method === "POST" && path === "/lineups") {
        api.previews.push(request.postDataJSON());
        return route.fulfill({ status: 200, contentType: "application/pdf", body: PDF });
      }
      if (method === "POST" && /^\/lineups\/saved\/[^/]+\/generate$/.test(path)) {
        return route.fulfill({ status: 200, contentType: "application/pdf", body: PDF });
      }
      api.unhandled.push(`${method} ${path}`);
      return json(route, { detail: "not mocked" }, 404);
    },
  );
}

export interface Fixtures {
  /** The fake backend for this test, already holding one team with players and saved lineups. */
  api: FakeApi;
  /** A page signed in as the owner of that team. */
  app: Page;
  /** A page nobody is signed in on. */
  guest: Page;
  /** Fails the test on a serious or critical accessibility violation on the current page. */
  expectAccessible: (page: Page) => Promise<void>;
  /** Fails when the page scrolls sideways, the usual way a layout breaks on a phone. */
  expectNoHorizontalScroll: (page: Page) => Promise<void>;
}

export const test = base.extend<Fixtures>({
  // Playwright needs the destructuring pattern even when a fixture uses no other fixture.
  // eslint-disable-next-line no-empty-pattern
  api: async ({}, use) => {
    const t = team("SZVTK");
    await use({
      teams: [t],
      players: makePlayers(t.id),
      saved: [makeSaved(t, 1), makeSaved(t, 2), makeSaved(t, 3)],
      previews: [],
      unhandled: [],
    });
  },
  app: async ({ page, api }, use) => {
    await install(page, api, true);
    await use(page);
    expect(api.unhandled, "API calls the fake backend does not know").toEqual([]);
  },
  guest: async ({ page, api }, use) => {
    await install(page, api, false);
    await use(page);
  },
  // eslint-disable-next-line no-empty-pattern
  expectAccessible: async ({}, use) => {
    await use(async (page) => {
      // `label-content-name-mismatch` (WCAG 2.5.3: a name starts with the visible text) is an
      // experimental rule, so it is off unless asked for.
      const { violations } = await new AxeBuilder({ page })
        .options({ rules: { "label-content-name-mismatch": { enabled: true } } })
        .analyze();
      const blocking = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(
        blocking.map(
          (v) =>
            `${v.id}: ${v.nodes.map((n) => `${n.target.join(" ")} (${n.any[0]?.message ?? ""})`).join(" | ")}`,
        ),
      ).toEqual([]);
    });
  },
  // eslint-disable-next-line no-empty-pattern
  expectNoHorizontalScroll: async ({}, use) => {
    await use(async (page) => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, "the page is wider than the screen").toBeLessThanOrEqual(0);
    });
  },
});

export { expect };
