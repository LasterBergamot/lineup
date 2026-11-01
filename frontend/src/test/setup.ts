import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { i18n } from "@/i18n";

// jsdom has no modal <dialog>: `showModal()` / `close()` only toggle `open` and `close()` fires the
// `close` event, which is all the Dialog component relies on (the browser adds the focus trap,
// the scrim and Esc itself, so those are covered by the e2e tests).
HTMLDialogElement.prototype.showModal = function showModal() {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function close() {
  this.removeAttribute("open");
  this.dispatchEvent(new Event("close"));
};

// The app defaults to Hungarian; the suite asserts on English text, so every test starts in
// English. `changeLanguage` does not touch localStorage (only `setLanguage` does), which keeps
// storage empty for the tests that assert nothing is persisted. Tests of the language switch
// itself set `hu` or click the switch explicitly.
beforeEach(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
  document.documentElement.classList.remove("dark");
  localStorage.clear();
});
