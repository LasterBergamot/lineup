---
version: alpha
name: Lineup
description: The Lineup design system. A deep teal primary, an amber highlight, soft rounded shapes and a calm light and dark theme, set in Google Sans Flex.
colors:
  background: "#f3f7f8"
  foreground: "#0b1f26"
  card: "#ffffff"
  muted: "#e8eff1"
  muted-foreground: "#4b5d65"
  accent: "#e0f1f4"
  border: "#dbe5e8"
  input: "#7d8f96"
  ring: "#02677f"
  primary: "#02677f"
  primary-foreground: "#ffffff"
  primary-hover: "#01566a"
  primary-soft: "#dff1f5"
  secondary: "#ffb500"
  secondary-foreground: "#2b1a03"
  success: "#0f7a4d"
  warning-soft: "#fff4d6"
  destructive: "#b8340f"
  destructive-soft: "#fdeee9"
  water: "#0aa5c0"
  dark-background: "#0e2329"
  dark-foreground: "#eaf3f5"
  dark-card: "#14303a"
  dark-muted: "#1a3842"
  dark-accent: "#1f4753"
  dark-border: "#2b4a56"
  dark-primary: "#2cc4de"
  dark-secondary: "#f0b429"
  dark-destructive: "#ff8a6b"
  dark-sidebar: "#112a32"
typography:
  page-title:
    fontFamily: Google Sans Flex
    fontSize: 30px
    fontWeight: 600
    lineHeight: 36px
  section:
    fontFamily: Google Sans Flex
    fontSize: 22px
    fontWeight: 600
    lineHeight: 28px
  card-title:
    fontFamily: Google Sans Flex
    fontSize: 18px
    fontWeight: 600
    lineHeight: 24px
  ui:
    fontFamily: Google Sans Flex
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
  label:
    fontFamily: Google Sans Flex
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
  caption:
    fontFamily: Google Sans Flex
    fontSize: 12px
    fontWeight: 500
    lineHeight: 16px
rounded:
  sm: 6px
  md: 10px
  lg: 14px
  xl: 20px
  pill: 9999px
---

# Lineup design system

The visual language of the web app. The tokens live in `src/index.css` (light in `:root`, dark in
`.dark`) and are exposed to Tailwind through `@theme inline`; components use the semantic tokens
(`bg-primary`, `text-muted-foreground`) and never raw hex. It replaces the earlier "Polaris" theme.
The decisions and the port plan are in `PLAN-ui-redesign.md` and `PLAN.md` (D14). A private visual
reference, the *Lineup Design System* artifact, shows every component in light and dark.

## Colors

- **Primary (`#02677f`, dark `#2cc4de`):** the one main action per view, links and the focus ring.
  `primary-hover` for the hover state, `primary-soft` for a quiet tinted fill.
- **Secondary (`#ffb500`, dark `#f0b429`):** amber highlight: the dot of the wordmark, an accent
  mark. **Never body text.**
- **Accent (`#e0f1f4`, dark `#1f4753`):** the soft hover and selected tint (a row, a menu item).
  It used to be a bright cyan fill; the bright cyan lives on as the decorative `water` token, never
  for text or state.
- **Success, warning-soft, destructive (and their `-soft` fills):** state colours. They always
  carry a word, and an icon where one fits, never colour alone.
- **Border (`#dbe5e8`):** decorative separators (below 3:1 contrast). A control's visible boundary
  is `input` (`#7d8f96`), which meets 3:1.
- **Background / card / muted / foreground:** the stage, the surface, quiet chrome and body text.
- **Overlay:** the scrim behind a dialog.
- The PDF preview sheet is paper: white in both themes.

## Typography

Google Sans Flex, self-hosted through Fontsource: the app must never request a third-party origin
(`documentation/Privacy-and-Security.md`, GDPR G14). Page title 30/36 semibold, section 22/28,
card title 18/24, UI text 14/20, field labels 14/20 medium, captions 12/16 medium. Inputs are 16px
on phones so iOS does not zoom on focus. Use tabular numbers for NSSZ and cap numbers.

## Shapes

Soft, not round: controls `radius-md` (10px), cards `radius-lg` (14px), dialogs and the preview
panel `radius-xl` (20px), badges and avatars `radius-pill`. `rounded-sm` is 6px.

## Elevation

Short and soft: `shadow-xs` buttons and inputs, `shadow-sm` cards, `shadow-md` toasts and the
preview panel, `shadow-lg` dialogs. The values change with the theme (`--elev-*` in `index.css`;
the `shadow-*` utilities point at them, because Tailwind would otherwise inline the light value).
Motion uses `--duration-fast/base/slow` (120/200/320 ms) and `--ease-standard`.

## Brand

- **Wordmark (every page):** the text "Lineup", bold, `letter-spacing: -0.035em`, `foreground`,
  followed by an amber dot of 0.26em on the baseline, 0.09em from the last letter. 22px in the
  sidebar and mobile top bar, 36px on the sign-in page. `components/brand.tsx` renders it; the dot is
  `aria-hidden`, so the name stays "Lineup".
- **L tile:** a teal rounded square with a white post and an amber bar. Only for the favicon
  (`public/favicon.svg`, which uses the light values because an SVG favicon cannot read the app's
  tokens), the installable-app icons (`pnpm icons`) and avatars. Never next to the wordmark.

## Do's and Don'ts

**Do**

- Do use `primary` for the one main action of a view.
- Do use semantic tokens instead of hex in components.
- Do pair every status colour with a word (and an icon where one fits).
- Do keep controls at 44px on touch (`pointer-coarse:`) and focus a 2px `ring` with a 2px offset.
- Do check both themes and phone width after a visual change.

**Don't**

- Don't use amber (`secondary`) for text or as the primary action.
- Don't use `border` as the only boundary of a control.
- Don't use `water` for text or state.
- Don't put the L tile next to the wordmark.
- Don't load fonts, icons or images from another origin.
