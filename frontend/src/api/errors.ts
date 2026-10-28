import type { TFunction } from "i18next";
import { i18n } from "@/i18n";

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
 * function. Returns the raw `Response` too, for callers that need a header.
 */
export async function requestWithResponse<T>(
  call: Promise<FetchResult<T>>,
): Promise<{ data: T; response: Response }> {
  let result: FetchResult<T>;
  try {
    result = await call;
  } catch {
    throw new ApiError(0);
  }
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(result.response.status, result.error);
  }
  return { data: result.data as T, response: result.response };
}

/** Like {@link requestWithResponse}, for callers that only need the data. */
export async function request<T>(call: Promise<FetchResult<T>>): Promise<T> {
  return (await requestWithResponse(call)).data;
}

export interface FieldError {
  /** Dotted form path such as `players.0.name` or `match`. */
  path: string;
  message: string;
}

/**
 * Pulls per-field messages out of a FastAPI/Pydantic 422 body. These are validation sentences
 * written by us or Pydantic (never echoes of the input), so they are safe to show next to the
 * field. Entries that do not point at a request body field are skipped.
 *
 * The sentences are English only: they come from the server and are shown as received. Known
 * gap of the Hungarian UI (#155); client-side validation, which runs first, is translated.
 */
export function fieldErrors(error: unknown): FieldError[] {
  if (!(error instanceof ApiError) || error.status !== 422) return [];
  const detail = (error.body as { detail?: unknown } | undefined)?.detail;
  if (!Array.isArray(detail)) return [];
  const found: FieldError[] = [];
  for (const item of detail as { loc?: unknown; msg?: unknown }[]) {
    if (!Array.isArray(item.loc) || item.loc[0] !== "body" || typeof item.msg !== "string")
      continue;
    const path = item.loc.slice(1).join(".");
    if (path) found.push({ path, message: item.msg.replace(/^Value error, /, "") });
  }
  return found;
}

/**
 * A short, user-facing sentence for a failure, in the current UI language. Deliberately
 * generic: no server text is shown. Components pass the `t` from `useTranslation()` so the
 * sentence re-renders when the language switches; without it the global instance is used.
 */
export function describeError(error: unknown, t: TFunction = i18n.t): string {
  if (!(error instanceof ApiError)) return t("errors.unknown");
  switch (error.status) {
    case 0:
      return t("errors.network");
    case 422:
      return t("errors.rejected");
    case 502:
    case 503:
      return t("errors.busy");
    case 504:
      return t("errors.timeout");
    default:
      return t("errors.server");
  }
}
