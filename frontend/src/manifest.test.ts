import { existsSync } from "node:fs";
import { describe, expect, it } from "vitest";
import indexHtml from "../index.html?raw";
import rawManifest from "../public/manifest.webmanifest?raw";

interface Icon {
  src: string;
  sizes: string;
  type: string;
  purpose?: string;
}

const manifest = JSON.parse(rawManifest) as {
  name: string;
  start_url: string;
  scope: string;
  display: string;
  theme_color: string;
  icons: Icon[];
};

describe("web-app manifest (public/manifest.webmanifest)", () => {
  it("opens the app full-screen from its root, in the brand colour of index.html", () => {
    expect(manifest.name).toBe("Lineup");
    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("/");
    expect(manifest.scope).toBe("/");
    expect(indexHtml).toContain(`name="theme-color" content="${manifest.theme_color}"`);
  });

  it("is linked from index.html together with the iOS icon", () => {
    expect(indexHtml).toContain('rel="manifest" href="/manifest.webmanifest"');
    expect(indexHtml).toContain('rel="apple-touch-icon" href="/apple-touch-icon.png"');
    expect(existsSync("public/apple-touch-icon.png")).toBe(true);
  });

  it("has the 192 and 512 px icons Chrome needs to offer installation, and a maskable one", () => {
    const sizes = manifest.icons.map((icon) => icon.sizes);
    expect(sizes).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    expect(manifest.icons.some((icon) => icon.purpose === "maskable")).toBe(true);
    for (const icon of manifest.icons) {
      expect(icon.type).toBe("image/png");
      expect(existsSync(`public${icon.src}`), `${icon.src} exists`).toBe(true);
    }
  });

  it("never asks for the viewport to be locked (pinch zoom stays available)", () => {
    expect(indexHtml).not.toMatch(/user-scalable\s*=\s*no|maximum-scale/);
  });
});
