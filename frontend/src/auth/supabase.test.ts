import { afterEach, beforeEach } from "vitest";

const { createClient, getSession } = vi.hoisted(() => ({
  createClient: vi.fn(),
  getSession: vi.fn(),
}));
vi.mock("@supabase/supabase-js", () => ({ createClient }));

/** A fresh copy of the module, so its cached client doesn't leak between tests. */
async function load() {
  vi.resetModules();
  return import("@/auth/supabase");
}

beforeEach(() => {
  createClient.mockReset();
  getSession.mockReset();
  createClient.mockReturnValue({ auth: { getSession } });
});

afterEach(() => vi.unstubAllEnvs());

function configure() {
  vi.stubEnv("VITE_SUPABASE_URL", "https://abcd.supabase.co");
  vi.stubEnv("VITE_SUPABASE_ANON_KEY", "sb_publishable_x");
}

describe("getSupabase", () => {
  it("creates one PKCE client from the public settings and reuses it", async () => {
    configure();
    const { getSupabase } = await load();
    expect(getSupabase()).toBe(getSupabase());
    expect(createClient).toHaveBeenCalledOnce();
    expect(createClient).toHaveBeenCalledWith("https://abcd.supabase.co", "sb_publishable_x", {
      auth: {
        flowType: "pkce",
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  });

  it("throws the configuration error when the build has no settings", async () => {
    const { getSupabase } = await load();
    expect(() => getSupabase()).toThrow("VITE_SUPABASE_URL");
    expect(createClient).not.toHaveBeenCalled();
  });
});

describe("getAccessToken", () => {
  it("returns the session's access token", async () => {
    configure();
    getSession.mockResolvedValue({ data: { session: { access_token: "abc" } } });
    const { getAccessToken } = await load();
    expect(await getAccessToken()).toBe("abc");
  });

  it("returns null when nobody is signed in", async () => {
    configure();
    getSession.mockResolvedValue({ data: { session: null } });
    const { getAccessToken } = await load();
    expect(await getAccessToken()).toBeNull();
  });

  it("returns null when sign-in is not configured, so public calls still work", async () => {
    const { getAccessToken } = await load();
    expect(await getAccessToken()).toBeNull();
  });

  it("does not hide unexpected errors", async () => {
    configure();
    createClient.mockImplementation(() => {
      throw new Error("unexpected");
    });
    const { getAccessToken } = await load();
    await expect(getAccessToken()).rejects.toThrow("unexpected");
  });
});
