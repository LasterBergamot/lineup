import { notifyUnauthorized, onUnauthorized } from "@/auth/events";

describe("unauthorized events", () => {
  it("tells every listener until it unsubscribes", () => {
    const first = vi.fn();
    const second = vi.fn();
    const stopFirst = onUnauthorized(first);
    const stopSecond = onUnauthorized(second);
    notifyUnauthorized();
    expect(first).toHaveBeenCalledOnce();
    expect(second).toHaveBeenCalledOnce();
    stopFirst();
    notifyUnauthorized();
    expect(first).toHaveBeenCalledOnce();
    expect(second).toHaveBeenCalledTimes(2);
    stopSecond();
  });

  it("does nothing when nobody listens", () => {
    expect(() => notifyUnauthorized()).not.toThrow();
  });

  it("lets a listener unsubscribe itself while being notified", () => {
    const other = vi.fn();
    const stopSelf = onUnauthorized(() => stopSelf());
    const stopOther = onUnauthorized(other);
    notifyUnauthorized();
    expect(other).toHaveBeenCalledOnce();
    stopOther();
  });
});
