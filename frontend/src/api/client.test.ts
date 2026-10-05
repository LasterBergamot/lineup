import { API_BASE_URL, createApi } from "@/api/client";

describe("api client", () => {
  it("defaults to the same-origin /api dev proxy when VITE_API_URL is unset", () => {
    expect(API_BASE_URL).toBe("/api");
  });

  it("sends typed requests to the configured base URL", async () => {
    const fetchMock = vi.fn(async () => Response.json({ status: "ok" }));
    const { data, response } = await createApi("http://localhost/api").GET("/health", {
      fetch: fetchMock,
    });
    expect(fetchMock).toHaveBeenCalledOnce();
    const request = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(request.url).toBe("http://localhost/api/health");
    expect(response.ok).toBe(true);
    expect(data).toEqual({ status: "ok" });
  });
});
