// A static `?url` import: Vite emits the worker as a same-origin asset and inlines only its URL
// string here. A dynamic `import("...?url")` would add a tiny extra module and a second request.
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

/**
 * Loads pdf.js on first use. The library is large, so it is a separate chunk that only people who
 * press Preview download. The worker file is bundled with the app: nothing is fetched from a CDN
 * (GDPR G14, and a strict CSP stays possible with `worker-src 'self'`).
 */
export async function loadPdfjs() {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
  return pdfjs;
}
