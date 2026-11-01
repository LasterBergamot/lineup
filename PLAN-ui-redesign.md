# UI redesign port plan

Working plan for porting the new "Lineup" design system into `frontend/`. Read it when picking up
that work; tick the checklists and add a progress-log row (with the real PR number) as items land;
delete this file once both PRs are merged. It replaces the "Polaris" theme (`frontend/DESIGN.md`).

**Visual reference:** the [Lineup Design System](https://claude.ai/artifact/YN2gjV1LsmA393RBwEzWbh)
artifact (private to the owner; the values an implementer needs are copied into the appendices
below, so the artifact is only a visual check). It shows tokens, Button, Input, Card, Badge, Tabs,
Dialog, Toast, ListRow, EmptyState, Navigation, Logo, and screen templates for sign-in, the lineup
creator (desktop and phone), saved lineups, roster and team, in light and dark.

## Decisions

- **Scope:** the whole system, including the new Dialog and Toast components.
- **Delivery:** two PRs, each from its own issue (file them with the `new-issue` skill; milestone and
  labels per `.claude/context/issues.md`). PR 1 is the visual foundation, PR 2 the components and
  screens. Branches `feat/<issue>-…` from `develop`; commit subjects `#N - …`.
- **No new dependencies.** Dialog uses the native `<dialog>` element (`showModal()` gives a focus trap,
  Esc and `aria-modal`). Toast and Tabs are small hand-written components. This avoids new Radix
  packages, a `task docs:references` regeneration and a new supply-chain surface.
- **`ConfirmButton` stays** as the destructive pattern for rows (documented in
  `.claude/rules/frontend.md`, covered by five test files). The Dialog is adopted for the phone
  preview sheet instead.
- **Keep the shadcn token names** so components change little. `accent` changes meaning: it becomes
  the soft hover and selected tint (it was a bright cyan fill). The bright cyan lives on as the
  decorative `water` token and is never used for text or state.
- **Logo:** a text wordmark ("Lineup" in bold with an amber dot) on every page; the "L tile" is only
  the favicon, the installable-app icons and avatars (appendix B).
- **Fonts stay self-hosted** (Fontsource Google Sans Flex). The artifact's previews load Google
  Fonts only for convenience; the app must never request a third-party origin
  (`documentation/Privacy-and-Security.md`, GDPR G14).
- Before coding each PR run `compliance-audit quick <issue#>` (`.claude/skills/compliance-audit`).
  Expected result: no compliance-relevant change, but confirm that toasts hold no personal data and
  use no storage.

## PR 1 — visual foundation (tokens, radii, shadows, dark theme, brand)

- [x] **Tokens in `frontend/src/index.css`.** Replace the Polaris values with appendix A (light in
  `:root`, dark in `.dark`). Remove `--radius: 0px` and the four `--radius-*` aliases at L73-76;
  define `--radius-sm/md/lg/xl` (6/10/14/20px) and `--radius-pill` directly in `@theme inline`. Add the
  new colour tokens to `@theme inline` (`primary-soft(-foreground)`, `primary-hover`,
  `secondary-hover`, `success*`, `warning-soft(-foreground)`, `destructive-soft(-foreground)`,
  `destructive-hover`, `overlay`, `water`), the `--shadow-xs/sm/md/lg` tokens (light and dark
  values) and `--duration-*`. Keep `@custom-variant dark`, the `dark` class on `<html>` and
  `public/theme-init.js` unchanged. The old `--warning` pair (L35-36, L66-67, L103-104) is replaced
  by `warning-soft`; the amber stays `secondary`.
- [x] **Wordmark.** `src/components/brand.tsx` renders the text "Lineup" (keep the `APP_NAME`
  constant) plus an `aria-hidden` amber dot `span` (`bg-secondary`), no `<img>`. Size 22px in the
  sidebar and mobile top bar (`app-shell.tsx:25`, `:56`), 36px on the sign-in page
  (`pages/sign-in-page.tsx:51`); `join-page.tsx:92` and `:151` also use `Brand`. The dot must not be a
  text node, so `getByText("Lineup")` and the heading tests (`auth/flow.test.tsx`,
  `pages/join-page.test.tsx`, `e2e/*.e2e.ts`) keep working.
- [x] **Favicon and icons.** `public/favicon.svg` becomes the L tile (appendix B). Update
  `scripts/make-icons.mjs` (the `TEAL`, `AMBER` and `ARROW` constants and the `svg()` template; the
  maskable icon keeps a safe zone, scale 0.65) and run `pnpm icons` for `icon-192.png`,
  `icon-512.png`, `icon-maskable-512.png` and `apple-touch-icon.png` (`LINEUP_CHROMIUM=…` skips the
  Chromium download). Update `theme_color` and `background_color` in `public/manifest.webmanifest`
  and the `theme-color` meta in `index.html` together: `src/manifest.test.ts:28` asserts they match.
- [x] **Selected saved row.** `features/saved/saved-lineups.tsx:126-127` drops
  `border-l-4 border-l-transparent` / `border-l-primary bg-accent` for a fill that is distinct from
  the hover tint (the design uses `bg-accent` plus a "Preview" badge from PR 2; for PR 1 use
  `bg-accent` with a font-medium title). Change the class assertions in
  `saved-lineups.test.tsx:130-133` and `e2e/saved.e2e.ts:14-17` to rely on `aria-current="true"`, which
  is already asserted next to them.
- [x] **Banners.** `backend-status/banner.tsx:23`, `:33` swap `bg-warning` and
  `text-warning-foreground` for the `warning-soft` tokens; recheck the "down" banner (`:42`) and its
  outline Retry button (`:45`) against `destructive`.
- [x] **Docs, same PR.** Rewrite `frontend/DESIGN.md` for the new system (tokens, shapes, elevation,
  do's and don'ts, wordmark, link to the artifact). Update `README.md` (L117, L344, L349, L352, L355),
  `documentation/Current-State-Frontend.md` (L14-15, L54-56, L64-68),
  `documentation/Roadmap-Frontend.md` (L16), `documentation/Newcomer-Guide.md` (L72),
  `documentation/References.md` handwritten rows (L37-38, L46), `.claude/rules/frontend.md` (Polaris and
  "square corners", the Saved highlight, dark-theme coverage) and the comment in `theme-toggle.tsx`.
  Add a new decision entry to `PLAN.md` (do not rewrite D11, it is history).
- [x] **Verify.** `task fe:check`, `task fe:e2e` (axe runs in light and dark on the four signed-in
  screens), and look at every screen in light, dark and phone width against the artifact.

## PR 2 — components and screens

- [ ] **Restyle `src/components/ui/`.** `button.tsx`: `rounded-md`, `shadow-xs`, hover via
  `primary-hover` / `secondary-hover` / `destructive-hover` instead of `/90`, outline and ghost hover
  `bg-accent`, keep `loading`, `asChild` and the `pointer-coarse:` 44px heights. `card.tsx`: `rounded-lg`,
  `shadow-sm`, 24px padding. `input.tsx` (`CONTROL`, shared by `Input` and `Select`): `rounded-md`,
  `border-input`, `bg-card`, `shadow-xs`; keep `h-10`, `pointer-coarse:h-11` and `text-base md:text-sm`
  (16px on phones). `field.tsx`, `skeleton.tsx` (rounded). Focus stays a 2px `ring` with a 2px offset.
- [ ] **Shell.** `app-shell.tsx`: active nav item uses `sidebar-accent` (soft) instead of the solid
  `bg-sidebar-primary` fill; the bottom nav's active item gets the soft pill; the sidebar footer's team
  label gets an initials avatar. Keep safe-area padding, 44px targets and `max-w-[1200px]`.
  `account-panel.tsx`, `language-switch.tsx` (pill segmented control, still `aria-pressed`, still
  `HU – Magyar` accessible names; its active state stops using the amber `secondary` button).
- [ ] **`ui/badge.tsx`.** Variants neutral, primary, success, warning, danger, outline (24px pill,
  12px text, icon plus word for status). Replaces the hand-made role label at
  `features/members/members-list.tsx:85` and adds the "Preview" badge on the selected saved row.
- [ ] **`ui/tabs.tsx`.** Segmented control with `role="tablist"` / `role="tab"` / `aria-selected`.
  Used for the Quick sheet toggle (`pages/lineup-page.tsx:55-65`), the cap colour and the invite expiry
  (`features/invitations/invite-panel.tsx`).
- [ ] **`ui/dialog.tsx`.** Wraps native `<dialog>` (`showModal()`, `aria-labelledby`/`aria-describedby`,
  scrim `overlay`, focus returns to the trigger, Esc cancels). Adopted for the phone preview sheet in
  `features/preview/preview-panel.tsx` (today a `fixed inset-0` aside with no focus trap).
- [ ] **`ui/toast.tsx`.** `ToastProvider` plus `useToast()` with an `aria-live` region, mounted in
  `src/app.tsx`. Success and info auto-dismiss after 5 s (pause on hover and focus); errors stay until
  dismissed; at most three at once. No storage and no personal data in messages (generic text such as
  "Lineup saved", never a player name or NSSZ number). Adopt for "Lineup saved"
  (`features/creator/lineup-creator.tsx`) and "Link copied" (`invite-panel.tsx`, which today swaps text
  inline at L148).
- [ ] **i18n.** Every new string goes through `t()` with identical keys in `src/i18n/locales/hu.json`
  and `en.json` (a test enforces parity). New `aria-label`s start with the visible verb (WCAG 2.5.3).
  `components/ui/` is exempt from the literal-string lint; Dialog and Toast callers are not.
- [ ] **Tests, 100 % coverage** (`task fe:coverage`). New unit tests for Badge, Tabs, Dialog and Toast
  (timers, hover pause, Esc, focus return, both locales). Update `app-shell.test.tsx`,
  `members-list`, `lineup-page`, `invite-panel` and `preview-panel` tests that touch changed markup.
  E2E: add dark-theme axe checks for sign-in, onboarding and the creator preview (today only the four
  signed-in screens run in dark), plus a Toast and a Dialog flow; `touch.e2e.ts` (44px targets, 16px
  inputs) and `expectNoHorizontalScroll` must stay green. In tests never write
  `beforeEach(() => mock.mockReset())` (see `.claude/rules/frontend.md`).
- [ ] **Docs, same PR.** `.claude/rules/frontend.md` (new components, Toast and Dialog rules,
  `ConfirmButton` unchanged), `documentation/Current-State-Frontend.md` component list,
  `frontend/DESIGN.md` component section, `documentation/Privacy-and-Security.md` only if something
  stored changes (expected: no). Then update the artifact's Dialog guidance to say `ConfirmButton`
  stays for rows.
- [ ] **Verify.** `task fe:check`, `task fe:e2e`, run the app (`task fe:dev` with `task up`) and compare
  every screen with the artifact in light, dark and phone width; check the favicon in a browser tab
  and the installed-app icon; check the network panel for third-party requests and `localStorage`
  for keys beyond the Supabase session, `lineup-theme` and `lineup-lang`.

## Progress log

| Date | Item | PR |
|------|------|----|
| 2026-11-01 | Plan written | #237 |
| 2026-11-01 | PR 1: visual foundation (tokens, wordmark, favicon, selected row, banners, docs), issue #238 | #240 |

---

## Appendix A — token values

Names match the current shadcn tokens in `frontend/src/index.css`. Light values go in `:root`, dark
values in `.dark`. Contrast was tuned by calculation, not with a checker: let the Playwright axe run
(`color-contrast`) confirm it.

```css
/* light */
--background: #f3f7f8;            --foreground: #0b1f26;
--card: #ffffff;                  --card-foreground: var(--foreground);
--popover: #ffffff;               --popover-foreground: var(--foreground);
--muted: #e8eff1;                 --muted-foreground: #4b5d65;
--accent: #e0f1f4;                --accent-foreground: var(--foreground);
--border: #dbe5e8;                --input: #7d8f96;                 --ring: #02677f;
--primary: #02677f;               --primary-foreground: #ffffff;    --primary-hover: #01566a;
--primary-soft: #dff1f5;          --primary-soft-foreground: #014f61;
--secondary: #ffb500;             --secondary-foreground: #2b1a03;  --secondary-hover: #e6a300;
--success: #0f7a4d;               --success-foreground: #ffffff;
--success-soft: #e0f4ea;          --success-soft-foreground: #0b5c3a;
--warning-soft: #fff4d6;          --warning-soft-foreground: #7a4f00;
--destructive: #b8340f;           --destructive-foreground: #ffffff; --destructive-hover: #9a2a0a;
--destructive-soft: #fdeee9;      --destructive-soft-foreground: #8f270a;
--overlay: rgba(6, 20, 24, 0.45); --water: #0aa5c0;
--sidebar: #ffffff;               --sidebar-foreground: var(--foreground);
--sidebar-primary: var(--primary);                --sidebar-primary-foreground: var(--primary-foreground);
--sidebar-accent: var(--primary-soft);            --sidebar-accent-foreground: var(--primary-soft-foreground);
--sidebar-border: var(--border);
--shadow-xs: 0 1px 2px rgba(11, 31, 38, 0.06);
--shadow-sm: 0 1px 3px rgba(11, 31, 38, 0.08), 0 1px 2px rgba(11, 31, 38, 0.04);
--shadow-md: 0 6px 16px rgba(11, 31, 38, 0.08), 0 2px 4px rgba(11, 31, 38, 0.04);
--shadow-lg: 0 20px 40px rgba(11, 31, 38, 0.16), 0 4px 8px rgba(11, 31, 38, 0.06);

/* dark */
--background: #0e2329;            --foreground: #eaf3f5;
--card: #14303a;                  --popover: #1b3b46;
--muted: #1a3842;                 --muted-foreground: #a9bcc3;
--accent: #1f4753;
--border: #2b4a56;                --input: #6d8893;                 --ring: #2cc4de;
--primary: #2cc4de;               --primary-foreground: #04181d;    --primary-hover: #5ad3e8;
--primary-soft: #164a58;          --primary-soft-foreground: #9fe6f3;
--secondary: #f0b429;             --secondary-foreground: #231503;  --secondary-hover: #ffc94d;
--success: #4cc38a;               --success-foreground: #04170e;
--success-soft: #17402f;          --success-soft-foreground: #9be6c1;
--warning-soft: #44350f;          --warning-soft-foreground: #f7d27e;
--destructive: #ff8a6b;           --destructive-foreground: #2a0a02; --destructive-hover: #ffa68d;
--destructive-soft: #4a2018;      --destructive-soft-foreground: #ffbca7;
--overlay: rgba(0, 0, 0, 0.55);   --water: #0b86a0;
--sidebar: #112a32;
--shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.4);
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.5);
--shadow-md: 0 6px 16px rgba(0, 0, 0, 0.5);
--shadow-lg: 0 20px 40px rgba(0, 0, 0, 0.6);
/* the unlisted dark tokens (card-foreground, popover-foreground, accent-foreground, sidebar-*) are
   the same aliases as in light */

/* theme-independent */
--radius-sm: 6px;  --radius-md: 10px;  --radius-lg: 14px;  --radius-xl: 20px;  --radius-pill: 9999px;
--duration-fast: 120ms;  --duration-base: 200ms;  --duration-slow: 320ms;  /* easing cubic-bezier(0.2, 0, 0, 1) */
```

Usage rules worth keeping in `DESIGN.md`: `primary` is the one main action per view; `secondary` (amber)
is a highlight and never body text; `border` is decorative (below 3:1), so a control's boundary is
`input`; `success`, `warning-soft` and `destructive` always carry an icon and a word, never colour alone;
the `.paper` PDF preview sheet is white in both themes. Scale: controls `radius-md`, cards
`radius-lg`, dialogs and the preview panel `radius-xl`, badges and avatars `radius-pill`; shadows
`xs` buttons and inputs, `sm` cards, `md` toasts and the preview panel, `lg` dialogs. Type stays
Google Sans Flex: page title 30/36 semibold, section 22/28, card title 18/24, UI text 14/20, field
labels 14/20 medium, captions 12/16 medium; inputs 16px on phones; tabular numbers for NSSZ and
cap numbers.

## Appendix B — brand

**Wordmark (every page).** The text "Lineup", bold (700), `letter-spacing: -0.035em`, colour
`foreground`, followed by a dot of 0.26em in `secondary` sitting on the baseline, 0.09em from the last
letter. 22px in the sidebar and mobile top bar, 36px on the sign-in page. Capital L, rest lowercase.
No symbol beside it.

**L tile (favicon, app icons, avatars).** A 32px rounded square in `primary`, a white
(`primary-foreground`) post and an amber (`secondary`) bar. For `public/favicon.svg` use the light
values, since an SVG favicon cannot read the app's tokens:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="9" fill="#02677f"/>
  <rect x="10" y="7" width="5" height="18" rx="2.5" fill="#ffffff"/>
  <rect x="10" y="20" width="13" height="5" rx="2.5" fill="#ffb500"/>
</svg>
```

`scripts/make-icons.mjs` should draw the same three shapes (the maskable icon needs the tile
full-bleed with the L inside the central safe zone). Use the tile only where a square icon is needed;
never put it next to the wordmark in the app chrome.

## Appendix C — what depends on the old design (from the exploration)

Paths are under `frontend/`. The app is semantic-token-only (no hex in components) and nothing uses
`rounded-*` today: square corners come purely from `--radius: 0px`, so adding `rounded-*` to the
`ui/` components works once the radii are redefined.

| Area | Where | Note |
|------|-------|------|
| Theme | `src/index.css` | L8 `--radius: 0px`; L21 `--accent` bright cyan; L35-36 and L66-67 `--warning` amber; no `--shadow-*` tokens exist |
| Selected row | `features/saved/saved-lineups.tsx:126-127` | the only `bg-accent` use; asserted in `saved-lineups.test.tsx:130-133` and `e2e/saved.e2e.ts:14-17` |
| Language switch | `components/language-switch.tsx:23` | the only consumer of the `secondary` button variant |
| Banners | `backend-status/banner.tsx:23,33,42,45` | `bg-warning`, `bg-destructive`, outline Retry |
| Nav | `components/app-shell.tsx:35,46,55,72` | solid `bg-sidebar-primary` active item; footer; mobile header; bottom nav |
| Brand | `components/brand.tsx` | `<img src="/favicon.svg">` + text; used by app-shell, sign-in, join (two places) |
| Surfaces | `ui/card.tsx:6`, `query-boundary.tsx:39`, `saved-lineups.tsx:114,120`, `preview-panel.tsx:24` | `border bg-card` boxes |
| Lists | `directory-card.tsx:80`, `invite-panel.tsx:166`, `members-list.tsx:74`, `players-card.tsx:76` | `divide-y border` |
| Inline errors | `lineup-creator.tsx:346,412`, `lineup-form.tsx:216`, `pdf-viewer.tsx:64`, `saved-lineups.tsx:196,213` | `border border-destructive p-3` |
| Role label | `members-list.tsx:85` | hand-made badge |
| Controls | `ui/button.tsx:8-27`, `ui/input.tsx:4-5` | ring and 44px rules to keep |
| Toggle | `pages/lineup-page.tsx:55-65` | two `aria-pressed` buttons, becomes Tabs |
| Mobile sheet | `features/preview/preview-panel.tsx` | `fixed inset-0`, no focus trap, becomes Dialog |

**Tests to keep green.** `e2e/touch.e2e.ts` (every control at least 44px tall, 16px inputs),
`e2e/saved.e2e.ts` (preview panel at least 359px wide on phones), `expectNoHorizontalScroll` on every
screen, axe including `color-contrast` and `label-content-name-mismatch` (`e2e/fixtures.ts:258-272`),
`e2e/screens.e2e.ts:11-33` (light and dark on `/`, `/roster`, `/saved`, `/members`),
`src/manifest.test.ts:28` (meta and manifest colours match), `app-shell.test.tsx:33,45` (nav labels,
no `aria-current` on Lineup), heading text "Lineup" in the auth, join, lineup and e2e tests, and
the `ConfirmButton` users (`members-page`, `players-card`, `saved-lineups`, `invite-panel`,
`team-settings-card` tests). The e2e job is report-only in CI today; the unit tests cannot check
colour contrast.

**Dependencies.** The only Radix package is `@radix-ui/react-slot`; this plan adds none.
