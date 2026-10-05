/** A failed API call. `status` is the HTTP status, or 0 when no response arrived at all. */
export class ApiError extends Error {
  readonly status: number;
  /** The parsed error body, if any. Shown to users only through `describeError`, never logged. */
  readonly body: unknown;

  constructor(status: number, body?: unknown) {
    super(status === 0 ? "Network error" : `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/**
 * True for failures worth retrying: no response at all (network down, server still booting) or
 * a gateway error (502/503/504, which Fly's proxy returns while a machine starts). Any other
 * 4xx/5xx is a real answer and retrying would just repeat it.
 */
export function isTransient(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 0 || [502, 503, 504].includes(error.status))
  );
}

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/**
 * Runs an `openapi-fetch` call and turns both failure modes (a rejected promise, an error
 * status) into a thrown {@link ApiError}, which is what TanStack Query expects from a query
 * function.
 */
export async function request<T>(call: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await call;
  } catch {
    throw new ApiError(0);
  }
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(result.response.status, result.error);
  }
  return result.data as T;
}

/** A short, user-facing sentence for a failure. Deliberately generic: no server text is shown. */
export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Something went wrong. Please try again.";
  switch (error.status) {
    case 0:
      return "Can't reach the server. Check your connection and try again.";
    case 422:
      return "Some of the entered details were rejected. Please check them and try again.";
    case 502:
    case 503:
      return "The server is busy or starting up. Please try again in a moment.";
    case 504:
      return "The server took too long to respond. Please try again.";
    default:
      return "Something went wrong on our side. Please try again.";
  }
}
