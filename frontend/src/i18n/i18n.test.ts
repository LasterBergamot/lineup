import { act } from "@testing-library/react";
import { i18n, LANGUAGE_STORAGE_KEY, setLanguage } from "@/i18n";
import { errorKey, translateError } from "@/i18n/error-key";
import en from "@/i18n/locales/en.json";
import hu from "@/i18n/locales/hu.json";

/** `a.b.c` paths of every string leaf in a locale bundle. */
function leafPaths(node: unknown, prefix = ""): string[] {
  if (typeof node === "string") return [prefix];
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    leafPaths(value, prefix ? `${prefix}.${key}` : key),
  );
}

function leaves(bundle: unknown): Map<string, string> {
  const result = new Map<string, string>();
  for (const path of leafPaths(bundle)) {
    result.set(
      path,
      path
        .split(".")
        .reduce((node, key) => (node as Record<string, unknown>)[key], bundle) as string,
    );
  }
  return result;
}

/** The `{{name, format}}` placeholders of a message, so a translation can't drop a value. */
function placeholders(message: string): string[] {
  return [...message.matchAll(/\{\{\s*(\w+)/g)].map((m) => m[1]!).sort();
}

describe("locale files", () => {
  it("have exactly the same keys in Hungarian and English", () => {
    expect([...leaves(hu).keys()].sort()).toEqual([...leaves(en).keys()].sort());
  });

  it("use the same placeholders in both languages", () => {
    const english = leaves(en);
    for (const [path, message] of leaves(hu)) {
      expect(placeholders(message), path).toEqual(placeholders(english.get(path)!));
    }
  });

  it("have no empty text", () => {
    for (const bundle of [hu, en]) {
      for (const [path, message] of leaves(bundle)) expect(message.trim(), path).not.toBe("");
    }
  });
});

/** Loads a fresh copy of the i18n module, as a page reload would. */
async function reload() {
  vi.resetModules();
  return import("@/i18n");
}

describe("language selection", () => {
  afterEach(() => {
    vi.resetModules();
  });

  it("is Hungarian on a first visit, and stores nothing", async () => {
    const fresh = await reload();
    expect(fresh.i18n.resolvedLanguage).toBe("hu");
    expect(fresh.i18n.t("nav.lineup")).toBe("Rajtlista");
    expect(document.documentElement.lang).toBe("hu");
    expect(localStorage.length).toBe(0);
  });

  it("ignores the browser's own language settings", async () => {
    vi.spyOn(window.navigator, "language", "get").mockReturnValue("en-US");
    vi.spyOn(window.navigator, "languages", "get").mockReturnValue(["en-US", "en"]);
    const fresh = await reload();
    expect(fresh.i18n.resolvedLanguage).toBe("hu");
    vi.restoreAllMocks();
  });

  it("restores the saved choice after a reload", async () => {
    await setLanguage("en");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    const fresh = await reload();
    expect(fresh.i18n.resolvedLanguage).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("falls back to Hungarian for a stored value it does not support", async () => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, "fr");
    const fresh = await reload();
    expect(fresh.i18n.resolvedLanguage).toBe("hu");
  });

  it("keeps <html lang> on Hungarian when i18next reports no resolved language", async () => {
    vi.doMock("i18next", () => ({
      default: {
        use() {
          return this;
        },
        init: vi.fn(async () => undefined),
        on: vi.fn(),
        resolvedLanguage: undefined,
      },
    }));
    try {
      document.documentElement.lang = "en";
      await reload();
      expect(document.documentElement.lang).toBe("hu");
    } finally {
      vi.doUnmock("i18next");
      vi.resetModules();
    }
  });

  it("writes only the lineup-lang key", async () => {
    await setLanguage("hu");
    expect(Object.keys(localStorage)).toEqual([LANGUAGE_STORAGE_KEY]);
  });

  it("still switches when storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    await setLanguage("hu");
    expect(i18n.resolvedLanguage).toBe("hu");
    vi.restoreAllMocks();
  });

  it("keeps <html lang> in step with every switch", async () => {
    await act(() => setLanguage("hu"));
    expect(document.documentElement.lang).toBe("hu");
    await act(() => setLanguage("en"));
    expect(document.documentElement.lang).toBe("en");
  });
});

describe("translateError", () => {
  it("translates an error key with its field label and re-translates on a switch", async () => {
    const message = errorKey("validation.tooLong", { field: "fields.match", max: 200 });
    expect(translateError(message)).toBe("Match can be at most 200 characters");
    await i18n.changeLanguage("hu");
    expect(translateError(message)).toBe("Mérkőzés legfeljebb 200 karakter lehet");
  });

  it("works for keys without parameters", () => {
    expect(translateError(errorKey("validation.minPlayers"))).toBe("Add at least one player");
  });

  it("passes any other text through untouched (server messages stay as received)", () => {
    expect(translateError("String should have at most 200 characters")).toBe(
      "String should have at most 200 characters",
    );
  });
});
