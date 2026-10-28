import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LanguageSwitch } from "@/components/language-switch";
import { i18n, LANGUAGE_STORAGE_KEY } from "@/i18n";

describe("LanguageSwitch", () => {
  it("names each language in its own language and marks the active one", () => {
    render(<LanguageSwitch />);
    expect(screen.getByRole("group", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
    const hungarian = screen.getByRole("button", { name: "Magyar" });
    expect(hungarian).toHaveAttribute("aria-pressed", "false");
    expect(hungarian).toHaveAttribute("lang", "hu");
  });

  it("switches the language, the group label and <html lang>, and remembers the choice", async () => {
    render(<LanguageSwitch />);
    await userEvent.click(screen.getByRole("button", { name: "Magyar" }));
    expect(i18n.resolvedLanguage).toBe("hu");
    expect(screen.getByRole("group", { name: "Nyelv" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Magyar" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.lang).toBe("hu");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("hu");
  });

  it("follows a language change made elsewhere", async () => {
    render(<LanguageSwitch />);
    await act(() => i18n.changeLanguage("hu"));
    expect(screen.getByRole("button", { name: "Magyar" })).toHaveAttribute("aria-pressed", "true");
  });
});
