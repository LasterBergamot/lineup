import { act, renderHook } from "@testing-library/react";
import { useMediaQuery } from "@/lib/use-media-query";

afterEach(() => {
  Reflect.deleteProperty(window, "matchMedia");
});

describe("useMediaQuery", () => {
  it("answers the fallback where there is no matchMedia", () => {
    expect(renderHook(() => useMediaQuery("(min-width: 1px)", true)).result.current).toBe(true);
    expect(renderHook(() => useMediaQuery("(min-width: 1px)", false)).result.current).toBe(false);
  });

  it("follows the query as it changes and stops listening on unmount", () => {
    let matches = false;
    let notify = () => {};
    const removed = vi.fn();
    window.matchMedia = vi.fn(() => ({
      get matches() {
        return matches;
      },
      addEventListener: (_event: string, listener: () => void) => {
        notify = listener;
      },
      removeEventListener: removed,
    })) as unknown as typeof window.matchMedia;
    const { result, unmount } = renderHook(() => useMediaQuery("(min-width: 1024px)", true));
    expect(result.current).toBe(false);
    matches = true;
    act(() => notify());
    expect(result.current).toBe(true);
    unmount();
    expect(removed).toHaveBeenCalled();
  });
});
