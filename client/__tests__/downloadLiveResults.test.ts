import {
  downloadLiveResults,
  filenameFromContentDisposition,
  sanitizeFilename,
} from "@features/live-quiz/lib/downloadLiveResults";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: { downloadResults: jest.fn() },
}));

const mockedDownload = liveQuizService.downloadResults as jest.Mock;

describe("filenameFromContentDisposition", () => {
  test("reads a quoted filename", () => {
    expect(
      filenameFromContentDisposition('attachment; filename="Class results.csv"'),
    ).toBe("Class results.csv");
  });

  test("prefers the RFC 5987 encoded filename", () => {
    expect(
      filenameFromContentDisposition(
        "attachment; filename=\"fallback.csv\"; filename*=UTF-8''Biolog%C3%ADa%20results.csv",
      ),
    ).toBe("Biología results.csv");
  });

  test("falls back to the plain filename when encoding is malformed", () => {
    expect(
      filenameFromContentDisposition(
        "attachment; filename=plain.csv; filename*=UTF-8''bad%E0%A4%A.csv",
      ),
    ).toBe("plain.csv");
  });

  test("returns null without a usable header", () => {
    expect(filenameFromContentDisposition(undefined)).toBeNull();
    expect(filenameFromContentDisposition("inline")).toBeNull();
  });
});

describe("sanitizeFilename", () => {
  test("replaces path separators and reserved characters", () => {
    expect(sanitizeFilename('Maths / Algebra: "Unit 1"?.csv')).toBe(
      "Maths - Algebra- -Unit 1-.csv",
    );
  });

  test("falls back to a default name when nothing usable remains", () => {
    expect(sanitizeFilename("   ")).toBe("live-quiz-results");
  });
});

describe("downloadLiveResults", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: jest.fn(() => "blob:results"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: jest.fn(),
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test("uses a sanitised fallback name and revokes the URL after a delay", async () => {
    mockedDownload.mockResolvedValue({
      blob: new Blob(["results"]),
      contentDisposition: null,
    });
    let downloadedAs = "";
    jest
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        downloadedAs = this.download;
      });

    await downloadLiveResults("quiz-1", "pdf", "Term 1/Week 2-results");

    expect(mockedDownload).toHaveBeenCalledWith("quiz-1", "pdf");
    expect(downloadedAs).toBe("Term 1-Week 2-results.pdf");
    expect(window.URL.revokeObjectURL).not.toHaveBeenCalled();

    jest.runAllTimers();
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:results");
  });
});
