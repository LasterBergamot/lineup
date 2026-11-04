import { AuthConfigError, readSupabaseConfig } from "@/auth/config";

const URL_OK = "https://abcd.supabase.co";

/** A JWT-shaped key (unsigned: only the payload is inspected) carrying the given role. */
function jwtWithRole(role: string): string {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, "");
  return `${encode({ alg: "HS256" })}.${encode({ role })}.signature`;
}

describe("readSupabaseConfig", () => {
  it("returns the URL (origin only) and the publishable key", () => {
    expect(
      readSupabaseConfig({
        VITE_SUPABASE_URL: ` ${URL_OK}/ `,
        VITE_SUPABASE_ANON_KEY: " sb_publishable_abc ",
      }),
    ).toEqual({ url: URL_OK, publishableKey: "sb_publishable_abc" });
  });

  it("accepts a legacy anon JWT", () => {
    const key = jwtWithRole("anon");
    expect(
      readSupabaseConfig({ VITE_SUPABASE_URL: URL_OK, VITE_SUPABASE_ANON_KEY: key }).publishableKey,
    ).toBe(key);
  });

  it.each([
    [{}, "not configured"],
    [{ VITE_SUPABASE_URL: URL_OK }, "not configured"],
    [{ VITE_SUPABASE_ANON_KEY: "k" }, "not configured"],
    [{ VITE_SUPABASE_URL: "   ", VITE_SUPABASE_ANON_KEY: "k" }, "not configured"],
  ])("rejects missing settings %j", (env, message) => {
    expect(() => readSupabaseConfig(env)).toThrow(message);
  });

  it("rejects an unparsable URL", () => {
    expect(() =>
      readSupabaseConfig({ VITE_SUPABASE_URL: "not a url", VITE_SUPABASE_ANON_KEY: "k" }),
    ).toThrow("not a valid URL");
  });

  it("requires https except on localhost", () => {
    const key = "sb_publishable_x";
    expect(() =>
      readSupabaseConfig({
        VITE_SUPABASE_URL: "http://abcd.supabase.co",
        VITE_SUPABASE_ANON_KEY: key,
      }),
    ).toThrow("https");
    expect(() =>
      readSupabaseConfig({ VITE_SUPABASE_URL: "ftp://localhost", VITE_SUPABASE_ANON_KEY: key }),
    ).toThrow("https");
    expect(
      readSupabaseConfig({
        VITE_SUPABASE_URL: "http://127.0.0.1:54399",
        VITE_SUPABASE_ANON_KEY: key,
      }).url,
    ).toBe("http://127.0.0.1:54399");
    expect(
      readSupabaseConfig({
        VITE_SUPABASE_URL: "http://localhost:54321",
        VITE_SUPABASE_ANON_KEY: key,
      }).url,
    ).toBe("http://localhost:54321");
  });

  it("refuses secret keys, which would be shipped to every browser", () => {
    for (const key of ["sb_secret_abc", jwtWithRole("service_role")]) {
      expect(() =>
        readSupabaseConfig({ VITE_SUPABASE_URL: URL_OK, VITE_SUPABASE_ANON_KEY: key }),
      ).toThrow(AuthConfigError);
    }
  });

  it("does not mistake other key shapes for a secret", () => {
    for (const key of ["plain-key", "a.%%%.c", `a.${btoa("not json")}.c`]) {
      expect(
        readSupabaseConfig({ VITE_SUPABASE_URL: URL_OK, VITE_SUPABASE_ANON_KEY: key })
          .publishableKey,
      ).toBe(key);
    }
  });

  it("reads the Vite environment by default", () => {
    expect(() => readSupabaseConfig()).toThrow(AuthConfigError);
    vi.stubEnv("VITE_SUPABASE_URL", URL_OK);
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "sb_publishable_env");
    expect(readSupabaseConfig().publishableKey).toBe("sb_publishable_env");
    vi.unstubAllEnvs();
  });

  describe("with VITE_AUTH_SAME_ORIGIN=true", () => {
    const key = "sb_publishable_x";
    const same = { VITE_AUTH_SAME_ORIGIN: "true", VITE_SUPABASE_ANON_KEY: key };
    const origin = "https://lineup.example.com";

    it("uses the page's own origin, with no VITE_SUPABASE_URL set", () => {
      expect(readSupabaseConfig(same, origin)).toEqual({ url: origin, publishableKey: key });
    });

    it("ignores VITE_SUPABASE_URL", () => {
      expect(readSupabaseConfig({ ...same, VITE_SUPABASE_URL: URL_OK }, origin).url).toBe(origin);
    });

    it("still refuses a non-local http origin", () => {
      expect(() => readSupabaseConfig(same, "http://lineup.example.com")).toThrow("https");
    });

    it("allows http on localhost, as in a local run of the image", () => {
      expect(readSupabaseConfig(same, "http://localhost:8090").url).toBe("http://localhost:8090");
    });

    it("still needs the key and still refuses a secret one", () => {
      expect(() => readSupabaseConfig({ VITE_AUTH_SAME_ORIGIN: "true" }, origin)).toThrow(
        "not configured",
      );
      expect(() =>
        readSupabaseConfig({ ...same, VITE_SUPABASE_ANON_KEY: "sb_secret_abc" }, origin),
      ).toThrow(AuthConfigError);
    });

    it.each(["false", "TRUE", "1", ""])("is off for %j: VITE_SUPABASE_URL is used", (flag) => {
      expect(
        readSupabaseConfig(
          { VITE_AUTH_SAME_ORIGIN: flag, VITE_SUPABASE_URL: URL_OK, VITE_SUPABASE_ANON_KEY: key },
          origin,
        ).url,
      ).toBe(URL_OK);
    });

    it("defaults the origin to the page's own", () => {
      expect(readSupabaseConfig(same).url).toBe(window.location.origin);
    });
  });
});
