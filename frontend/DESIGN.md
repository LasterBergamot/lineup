---
version: alpha
name: Polaris
description: A sharp shadcn/ui theme with a deep teal primary, an amber secondary, and square corners. by tweakcn.
colors:
  background: "#f5fafb"
  foreground: "#081e24"
  card: "#fcffff"
  primary: "#02677f"
  primary-foreground: "#ffffff"
  secondary: "#ffb500"
  secondary-foreground: "#321c04"
  muted: "#e4eef0"
  muted-foreground: "#5a6569"
  accent: "#03a2bc"
  accent-foreground: "#ffffff"
  destructive: "#d3451e"
  border: "#d4e1e4"
  input: "#b3c0c4"
  ring: "#02677f"
  sidebar: "#f5fafb"
  sidebar-foreground: "#030d11"
  sidebar-primary: "#02677f"
  chart-1: "#02677f"
  chart-2: "#ffb500"
  chart-3: "#309b42"
  chart-4: "#03a2bc"
  chart-5: "#d3451e"
  dark-background: "#020608"
  dark-foreground: "#d2d9da"
  dark-card: "#060e11"
  dark-primary: "#03a2bc"
  dark-secondary: "#eaaa2c"
  dark-muted: "#111d20"
  dark-muted-foreground: "#80888a"
  dark-accent: "#084150"
  dark-border: "#1e2b30"
  dark-sidebar: "#010405"
  dark-destructive: "#e45937"
typography:
  display:
    fontFamily: Google Sans Flex
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Google Sans Flex
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Google Sans Flex
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.25
  body-lg:
    fontFamily: Google Sans Flex
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.65
  body-md:
    fontFamily: Google Sans Flex
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.65
  body-sm:
    fontFamily: Google Sans Flex
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-md:
    fontFamily: Google Sans Flex
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
  sans-ui:
    fontFamily: Google Sans Flex
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: Google Sans Flex
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  xs: 0px
  sm: 0px
  md: 0px
  lg: 0px
  xl: 0px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  "2xl": 48px
  section: 64px
  gutter: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.secondary-foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  button-outline:
    backgroundColor: transparent
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    padding: 24px
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: 12px
  sidebar:
    backgroundColor: "{colors.sidebar}"
    textColor: "{colors.sidebar-foreground}"
---

# Polaris

A premade shadcn/ui theme by [tweakcn](https://tweakcn.com). Install tokens with `npx shadcn@latest add @shadcnblocks/theme/polaris`, then keep this DESIGN.md in the project root (or `.agents/`) so coding agents stay on-brand.

## Overview

Polaris is an instrument theme: pale stage (`#f5fafb`), deep teal primary (`#02677f`), and amber secondary (`#ffb500`). Dark mode drops the stage to near-black (`#020608`) and lifts the teal to `#03a2bc`.

It is **sharp, navigational, and two-tone**. It suits tools that can hold teal for action and amber for the supporting mark.

**Google Sans Flex** leads display, UI, and reading text. **Google Sans Flex** is for code.

Emotional targets: precise, north-pointing, square — never rounded, never a single hue.

## Colors

- **Primary (`#02677f`):** Deep teal — primary buttons and brand marks. Pair with white text (`#ffffff`). In dark mode the primary is `#03a2bc` with near-black labels (`#010406`).
- **Accent (`#03a2bc`):** Quiet highlight (`#03a2bc`) with text `#ffffff` for selected chips.
- **Secondary (`#ffb500`):** Supporting actions and quiet structure. Text `#321c04`.
- **Foreground (`#081e24`):** Body text. Do not swap it for a random gray.
- **Background (`#f5fafb`):** Page stage.
- **Card (`#fcffff`):** Content surfaces.
- **Muted (`#e4eef0`):** Quiet chrome. Muted text is `#5a6569`.
- **Border (`#d4e1e4`):** Structural lines. Prefer these over heavy shadows.
- **Destructive (`#d3451e` / dark `#e45937`):** Errors only. Keep them distinct from the brand color when the hues differ.
- **Ring (`#02677f`):** Focus ring.

Dark mode stage is `#020608`, cards `#060e11`, foreground `#d2d9da`.

## Typography

**Google Sans Flex** leads display, UI, and reading text. **Google Sans Flex** is for code.

- **Display / headlines:** Google Sans Flex SemiBold, tight tracking.
- **Body / reading:** Google Sans Flex Regular at 16–18px, line-height about 1.65.
- **UI chrome / labels:** Google Sans Flex Medium or Regular. Sentence case.
- **Mono:** Google Sans Flex for code, tokens, and IDs.

Do not set a separate serif for long-form text. This theme keeps Google Sans Flex for reading and UI.

## Layout

Use the semantic stage, then cards, then one primary action.

- Base spacing is an 8px scale. Section rhythm is about 64px.
- Prefer a readable prose column (~65–75ch) and a wider shell (~1200px) for app chrome.
- One primary action per view.

## Elevation & Depth

Depth is **soft and short**. Let borders and a single filled button carry emphasis.

- Prefer semantic surfaces: background, then card, then the primary action.
- Dark mode elevates with the dark card color, not bright white borders.

## Shapes

Radius is **sharp** — base `--radius` is `0px`. Keep corners square.

- Controls: 0px.
- Cards: 0px.
- Full pills only for avatars, if a circle is required.

## Components

Built for the shadcn/ui token contract. Prefer semantic tokens (`bg-primary`, `text-muted-foreground`) over raw hex in component code.

- **Primary button:** `#02677f` fill, `#ffffff` label.
- **Secondary button:** `#ffb500` fill, `#321c04` label.
- **Cards:** `#fcffff` surface, `#d4e1e4` border, padding about 24px.
- **Inputs:** stage or card fill, border `#d4e1e4`, focus ring `#02677f`.
- **Sidebar:** `#f5fafb` with `#030d11` labels. Do not paint the whole nav in primary.
- **Charts:** `#02677f`, `#ffb500`, `#309b42`, `#03a2bc`, `#d3451e` in that order.

## Do's and Don'ts

**Do**

- Do keep corners square.
- Do use teal for the primary action and amber for the secondary.
- Do set UI, reading text, and code in Google Sans Flex.
- Do support light and dark with the same teal-and-amber story.
- Do use shadcn semantic tokens instead of one-off hex in components.

**Don't**

- Don't round buttons, cards, or inputs.
- Don't swap amber in as the primary.
- Don't flood backgrounds with teal.
- Don't invent extra brand colors when a token already exists.
