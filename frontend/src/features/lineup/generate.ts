import { generateApi } from "@/api/client";
import { requestWithResponse } from "@/api/errors";
import type { components } from "@/api/schema";
import { filenameFromContentDisposition, type GeneratedFile } from "@/features/lineup/download";

export type LineupFormat = "pdf" | "docx";

type LineupRequest = components["schemas"]["LineupRequest"];

/** Reads the file out of a generate response, with the name from `Content-Disposition`. */
function toFile(data: Blob, response: Response, format: LineupFormat): GeneratedFile {
  return {
    blob: data,
    filename: filenameFromContentDisposition(
      response.headers.get("content-disposition"),
      `lineup.${format}`,
    ),
  };
}

/**
 * Calls `POST /lineups/saved/{id}/generate` and returns the file of an already saved lineup.
 * Throws `ApiError`: 404 for a lineup that is gone or belongs to a team the caller is not in,
 * 429/503/504 like {@link generateLineup}. Uses the long-timeout client for the PDF.
 */
export async function generateSavedLineup(
  id: string,
  format: LineupFormat,
  client: Pick<typeof generateApi, "POST"> = generateApi,
): Promise<GeneratedFile> {
  const { data, response } = await requestWithResponse(
    client.POST("/lineups/saved/{lineup_id}/generate", {
      params: { path: { lineup_id: id }, query: { format } },
      parseAs: "blob",
    }),
  );
  return toFile(data, response, format);
}

/**
 * Calls `POST /lineups` (nothing is stored server-side) and returns the file. Throws `ApiError`
 * on any failure; a 422 carries per-field messages (see `fieldErrors`). PDF generation uses the
 * long-timeout client because LibreOffice can take a while after a cold start.
 */
export async function generateLineup(
  body: LineupRequest,
  format: LineupFormat,
  client: Pick<typeof generateApi, "POST"> = generateApi,
): Promise<GeneratedFile> {
  const { data, response } = await requestWithResponse(
    client.POST("/lineups", { body, params: { query: { format } }, parseAs: "blob" }),
  );
  return {
    blob: data,
    filename: filenameFromContentDisposition(
      response.headers.get("content-disposition"),
      `lineup.${format}`,
    ),
  };
}
