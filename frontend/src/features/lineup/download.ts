/** A file the API produced, ready to hand to the browser's download mechanism. */
export interface GeneratedFile {
  blob: Blob;
  filename: string;
}

function safeName(name: string): string {
  // The name comes from a response header; never let it carry a path into the download.
  return name.replace(/[\\/\p{Cc}]/gu, "_").trim();
}

/**
 * Reads the download name out of a `Content-Disposition` header. Prefers the RFC 6266
 * `filename*=UTF-8''...` form (the backend sends it so `ő`/`ű` survive) and falls back to the
 * plain ASCII `filename="..."`, then to `fallback`.
 */
export function filenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const extended = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header);
  if (extended?.[1]) {
    try {
      const decoded = safeName(decodeURIComponent(extended[1].trim()));
      if (decoded) return decoded;
    } catch {
      // Malformed percent-encoding: try the plain form instead.
    }
  }
  const plain = /filename\s*=\s*"?([^";]+)"?/i.exec(header);
  const name = plain?.[1] ? safeName(plain[1]) : "";
  return name || fallback;
}

/**
 * Starts a browser download of `file`. The temporary object URL is released right away, so the
 * document (which contains personal data) does not stay referenced in memory.
 */
export function saveFile({ blob, filename }: GeneratedFile): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
