import js from "@eslint/js";
import i18next from "eslint-plugin-i18next";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "coverage",
      "public",
      "src/api/schema.d.ts",
      "playwright-report",
      "test-results",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  {
    // User-facing text must go through `t()` (#155). `jsx-only` checks JSX text and the string
    // attributes below; tests, the generated API types and the shadcn-style primitives (which
    // hold no copy) are out of scope.
    files: ["src/**/*.tsx"],
    ignores: ["src/**/*.test.tsx", "src/test/**", "src/components/ui/**"],
    plugins: { i18next },
    rules: {
      "i18next/no-literal-string": [
        "error",
        {
          mode: "jsx-only",
          "jsx-attributes": {
            // Attributes that carry text a person reads or hears.
            include: ["alt", "aria-label", "aria-description", "placeholder", "title"],
            exclude: [],
          },
          // `t("key")` is the translation call itself; react-hook-form's `register("name")` is a field path.
          callees: { exclude: ["i18n(ext)?", "t", "register"] },
        },
      ],
    },
  },
  {
    // Playwright fixtures are functions that call `use(...)`, which is not a React hook.
    files: ["e2e/**/*.ts"],
    rules: { "react-hooks/rules-of-hooks": "off" },
  },
  {
    // Node scripts (run by hand, e.g. `pnpm icons`).
    files: ["scripts/**/*.mjs"],
    languageOptions: { globals: globals.node },
  },
);
