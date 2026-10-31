import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 5173,
      strictPort: true,
      // Same-origin /api in dev means no CORS setup is needed locally.
      proxy: {
        "/api": {
          target: env.VITE_DEV_API_TARGET || "http://localhost:8000",
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api/, ""),
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
      coverage: {
        provider: "v8",
        // Count every source file, also the ones no test imports, so a missing test shows up.
        include: ["src/**/*.{ts,tsx}"],
        exclude: [
          "src/**/*.test.{ts,tsx}",
          "src/test/**",
          // Generated from the backend's OpenAPI spec (`task fe:api`), never edited by hand.
          "src/api/schema.d.ts",
          "src/vite-env.d.ts",
          // Bootstrap only: mounts <App /> into the page, which jsdom tests do not do.
          "src/main.tsx",
        ],
        reporter: ["text"],
        // Like the backend: new code needs tests, so anything below 100 % fails CI. Do not lower
        // these to get a change through; write the test (or delete the dead code).
        thresholds: { statements: 100, branches: 100, functions: 100, lines: 100 },
      },
    },
  };
});
