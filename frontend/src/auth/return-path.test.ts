import { afterEach } from "vitest";
import {
  clearReturnPath,
  readReturnPath,
  rememberReturnPath,
  safeReturnPath,
} from "@/auth/return-path";

afterEach(() => sessionStorage.clear());

describe("safeReturnPath", () => {
  it("keeps paths on this site, with their query and hash", () => {
    expect(safeReturnPath("/")).toBe("/");
    expect(safeReturnPath("/roster")).toBe("/roster");
    expect(safeReturnPath("/saved?page=2#top")).toBe("/saved?page=2#top");
  });

  it.each([
    ["nothing", undefined],
    ["null", null],
    ["empty", ""],
    ["a relative path", "roster"],
    ["another origin", "https://evil.example/"],
    ["a protocol-relative URL", "//evil.example/x"],
    ["a backslash trick", "/\\evil.example"],
    ["a javascript URL", "javascript:alert(1)"],
    ["a control character", "/a\nb"],
    ["a tab trick", "/\t/evil.example"],
  ])("falls back to the home page for %s", (_name, raw) => {
    expect(safeReturnPath(raw)).toBe("/");
  });
});

describe("remembered return path", () => {
  it("round-trips a safe path and forgets it on request", () => {
    expect(readReturnPath()).toBe("/");
    rememberReturnPath("/roster");
    expect(readReturnPath()).toBe("/roster");
    clearReturnPath();
    expect(readReturnPath()).toBe("/");
  });

  it("never stores or returns an unsafe path", () => {
    rememberReturnPath("//evil.example");
    expect(readReturnPath()).toBe("/");
    sessionStorage.setItem("lineup-return-to", "https://evil.example");
    expect(readReturnPath()).toBe("/");
  });
});
