import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { useAfterDelay } from "@/lib/use-after-delay";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("useAfterDelay", () => {
  it("turns true only after the delay has passed while active", () => {
    const { result } = renderHook(() => useAfterDelay(true, 5000));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(4999));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe(true);
  });

  it("never fires for work that finishes quickly, and resets afterwards", () => {
    const { result, rerender } = renderHook(({ active }) => useAfterDelay(active, 5000), {
      initialProps: { active: true },
    });
    act(() => vi.advanceTimersByTime(2000));
    rerender({ active: false });
    act(() => vi.advanceTimersByTime(10_000));
    expect(result.current).toBe(false);

    rerender({ active: true });
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(5000));
    expect(result.current).toBe(true);
    rerender({ active: false });
    expect(result.current).toBe(false);
  });
});
