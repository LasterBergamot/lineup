import { generateApi } from "@/api/client";
import { requestWithResponse } from "@/api/errors";
import type { components } from "@/api/schema";
import { filenameFromContentDisposition, type GeneratedFile } from "@/features/lineup/download";

export type LineupFormat = "pdf" | "docx";

type LineupRequest = components["schemas"]["LineupRequest"];

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
