import {
  liveQuizService,
  type LiveResultsExportFormat,
} from "@features/live-quiz/api/liveQuizService";

const DEFAULT_FILENAME = "live-quiz-results";

/**
 * Extract a filename from a Content-Disposition header. Prefers the RFC 5987
 * `filename*=UTF-8''...` form, which carries non-ASCII titles, over `filename=`.
 */
export function filenameFromContentDisposition(
  header: string | null | undefined,
): string | null {
  if (!header) return null;

  const encoded = header.match(/filename\*\s*=\s*([^']*)'[^']*'([^;]+)/i);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[2].trim().replace(/^"|"$/g, ""));
    } catch {
      // Malformed percent-encoding: fall back to the plain parameter.
    }
  }

  const plain = header.match(/filename\s*=\s*"?([^";]+)"?/i);
  return plain ? plain[1].trim() : null;
}

/** Replace characters that are unsafe in filenames and cap the length. */
export function sanitizeFilename(name: string): string {
  const cleaned = name
    .replace(/[\\/:*?"<>|\u0000-\u001f]+/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 150);
  return cleaned || DEFAULT_FILENAME;
}

/**
 * Fetch a server-generated results export and save it in the browser.
 * Prefers the filename from Content-Disposition; falls back to `fallbackName`.
 */
export async function downloadLiveResults(
  quizId: string,
  format: LiveResultsExportFormat,
  fallbackName: string,
): Promise<void> {
  const { blob, contentDisposition } = await liveQuizService.downloadResults(
    quizId,
    format,
  );
  const filename = sanitizeFilename(
    filenameFromContentDisposition(contentDisposition) ||
      `${fallbackName}.${format}`,
  );
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking synchronously can cancel the download in some browsers (older Safari).
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}
