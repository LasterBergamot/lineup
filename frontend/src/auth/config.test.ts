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
});
