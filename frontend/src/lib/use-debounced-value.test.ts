import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { useDebouncedValue } from "@/lib/use-debounced-value";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("useDebouncedValue", () => {
  it("returns the first value straight away", () => {
    const { result } = renderHook(() => useDebouncedValue("a", 300));
    expect(result.current).toBe("a");
  });

  it("follows a change only after it has stood still for the delay", () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 300), {
      initialProps: { value: "" },
    });
    rerender({ value: "S" });
    act(() => vi.advanceTimersByTime(299));
    expect(result.current).toBe("");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("S");
  });

  it("skips the values typed in between and restarts the wait on every change", () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 300), {
      initialProps: { value: "" },
    });
    rerender({ value: "S" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "Sz" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "Sze" });
    act(() => vi.advanceTimersByTime(200));
    expect(result.current).toBe("");
    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe("Sze");
  });

  it("leaves no timer running after unmounting", () => {
    const { rerender, unmount } = renderHook(({ value }) => useDebouncedValue(value, 300), {
      initialProps: { value: "" },
    });
    rerender({ value: "S" });
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
