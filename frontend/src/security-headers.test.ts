import { describe, expect, it } from "vitest";
import rawCaddyfile from "../docker/Caddyfile?raw";
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

/** Reads the `header <Name> "<value>"` lines of the Caddyfile (not the `header @matcher ...` ones). */
function parseCaddyHeaders(text: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const match = /^\s*header\s+([A-Za-z][A-Za-z-]*)\s+"(.*)"\s*$/.exec(line);
    if (match) found[match[1] as string] = match[2] as string;
  }
  return found;
}

describe("self-hosted web image headers and routes (docker/Caddyfile)", () => {
  const caddy = parseCaddyHeaders(rawCaddyfile);
  const pagesHeaders = parseHeaders(rawHeaders)["/*"] ?? {};

  it("sets every header of public/_headers, with the same value", () => {
    // Pages and the self-hosted image must send the same baseline, so they cannot drift apart.
    expect(Object.keys(pagesHeaders).length).toBeGreaterThan(0);
    for (const [name, value] of Object.entries(pagesHeaders)) {
      expect(caddy[name], name).toBe(value);
    }
  });

  it("has no log directive: invite codes are URL path segments and must not reach a log", () => {
    expect(rawCaddyfile).not.toMatch(/^\s*log\b/m);
  });

  it("proxies only the allow-listed Auth paths, none of them an admin path", () => {
    const line = /^\s*@auth path (.+)$/m.exec(rawCaddyfile)?.[1] ?? "";
    const paths = line.trim().split(/\s+/);
    expect(paths).toEqual([
      "/auth/v1/authorize",
      "/auth/v1/callback",
      "/auth/v1/token",
      "/auth/v1/logout",
      "/auth/v1/user",
      "/auth/v1/settings",
      "/auth/v1/.well-known/jwks.json",
    ]);
    for (const path of paths) {
      expect(path).not.toMatch(/admin|signup|\*/);
    }
  });

  it("answers 404 for every other Auth path, after the allow-list has had its turn", () => {
    const block = /^\s*handle \/auth\/v1\/\* \{\s*respond 404\s*\}/m.exec(rawCaddyfile);
    expect(block).not.toBeNull();
    // `handle` blocks are tried in order and the first match wins.
    expect(rawCaddyfile.indexOf("handle @auth")).toBeGreaterThan(-1);
    expect(rawCaddyfile.indexOf("handle @auth")).toBeLessThan(block?.index ?? -1);
  });
});
