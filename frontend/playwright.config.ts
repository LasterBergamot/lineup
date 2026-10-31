import { defineConfig } from "@playwright/test";

/**
 * Browser tests (#159): the real production bundle, in Chromium, at a phone and a desktop size.
 *
 * Nothing leaves the machine: `e2e/fixtures.ts` answers every API and Supabase request in the
 * browser, so no backend, database or Google account is needed. The bundle is built with a
 * local, fake Supabase URL and a made-up publishable key.
 *
 * Locally, point `LINEUP_CHROMIUM` at an installed Chromium (e.g. `/usr/bin/chromium`) to skip
 * Playwright's own browser download; CI runs `playwright install --with-deps chromium`.
 */
const PORT = 4173;
const executablePath = process.env.LINEUP_CHROMIUM || undefined;

export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    launchOptions: { executablePath },
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "phone",
      use: {
        viewport: { width: 360, height: 740 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
    { name: "desktop", use: { viewport: { width: 1280, height: 800 } } },
  ],
  webServer: {
    command: `pnpm build && pnpm exec vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      VITE_SUPABASE_URL: "http://127.0.0.1:54399",
      VITE_SUPABASE_ANON_KEY: "sb_publishable_e2e",
      VITE_API_URL: "",
      VITE_COLD_START_NOTICE: "false",
    },
  },
});
