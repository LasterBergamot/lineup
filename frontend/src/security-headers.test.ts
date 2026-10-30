import { describe, expect, it } from "vitest";
import rawHeaders from "../public/_headers?raw";

/** Parses a Cloudflare Pages `_headers` file into `{ path: { header: value } }`. */
function parseHeaders(text: string): Record<string, Record<string, string>> {
  const rules: Record<string, Record<string, string>> = {};
  let current: Record<string, string> | null = null;
  for (const line of text.split("\n")) {
    if (!line.trim() || line.trimStart().startsWith("#")) continue;
    if (!/^\s/.test(line)) {
      current = {};
      rules[line.trim()] = current;
      continue;
    }
    const [name = "", ...value] = line.trim().split(":");
    if (current) current[name.trim()] = value.join(":").trim();
  }
  return rules;
}

describe("Cloudflare Pages security headers (public/_headers)", () => {
  const headers = parseHeaders(rawHeaders)["/*"] ?? {};

  it("covers every path with the baseline headers", () => {
    expect(headers["Strict-Transport-Security"]).toMatch(/^max-age=\d{8,}/);
    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["Referrer-Policy"]).toBe("no-referrer");
    expect(headers["Permissions-Policy"]).toContain("camera=()");
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
  });

  it("does not ship a 404.html, which would switch Pages out of SPA mode", () => {
    // Without a top-level 404.html Pages serves index.html for unknown paths, so deep links
    // such as /join/:code reach the router. Adding one silently breaks that.
    expect(Object.keys(import.meta.glob("../public/404.html"))).toEqual([]);
  });
});
