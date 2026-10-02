import {
  liveQuizService,
  type LiveResultsExportFormat,
} from "@features/live-quiz/api/liveQuizService";

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
  const filename =
    contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1] ||
    `${fallbackName}.${format}`;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
