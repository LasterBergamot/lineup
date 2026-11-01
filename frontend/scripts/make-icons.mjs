// Renders the app icons in `public/` from the same mark as `public/favicon.svg`.
// Run `pnpm icons` (set LINEUP_CHROMIUM to a Chromium binary to skip Playwright's own download).
// The PNGs are committed, so this only needs to run when the logo changes.
import { chromium } from "@playwright/test";
import { writeFile } from "node:fs/promises";

const TEAL = "#02677f";
const WHITE = "#ffffff";
const AMBER = "#ffb500";

/**
 * The "L tile" of `public/favicon.svg`: a white post and an amber bar on a teal square. The icons
 * are full-bleed (no rounded corners, the OS masks them). `scale` shrinks the L towards the
 * centre: a maskable icon keeps it inside the safe zone.
 */
const svg = (scale) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%">` +
  `<rect width="32" height="32" fill="${TEAL}"/>` +
  `<g transform="translate(16 16) scale(${scale}) translate(-16 -16)">` +
  `<rect x="10" y="7" width="5" height="18" rx="2.5" fill="${WHITE}"/>` +
  `<rect x="10" y="20" width="13" height="5" rx="2.5" fill="${AMBER}"/></g></svg>`;

const ICONS = [
  { file: "icon-192.png", size: 192, scale: 1 },
  { file: "icon-512.png", size: 512, scale: 1 },
  { file: "icon-maskable-512.png", size: 512, scale: 0.65 },
  { file: "apple-touch-icon.png", size: 180, scale: 0.85 },
];

const browser = await chromium.launch({ executablePath: process.env.LINEUP_CHROMIUM || undefined });
const page = await browser.newPage();
for (const { file, size, scale } of ICONS) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(`<style>html,body{margin:0;height:100%}</style>${svg(scale)}`);
  await writeFile(new URL(`../public/${file}`, import.meta.url), await page.screenshot());
}
await browser.close();
