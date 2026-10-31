/**
 * Loads pdf.js on first use. The library is large, so it is a separate chunk that only people who
 * press Preview download. The worker file is bundled with the app (`?url` makes Vite emit it as a
 * same-origin asset): nothing is fetched from a CDN (GDPR G14, and a strict CSP stays possible).
 */
export async function loadPdfjs() {
  const [pdfjs, worker] = await Promise.all([
    import("pdfjs-dist"),
    import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
  ]);
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
  return pdfjs;
}
