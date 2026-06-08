import { useEffect, useRef, useState } from "react";
import { QuizGenerationSectionProps } from "@shared/types/props";
import RequiredLabel from "./common/RequiredLabel";

const QUESTION_TYPES = [
  { label: "Multiple Choice", value: "multichoice" },
  { label: "True/False", value: "true-false" },
  { label: "Short Answer", value: "short-answer" },
  { label: "Open Ended", value: "open-ended" },
];

export default function QuizGenerationSection({
  generationMode,
  setGenerationMode,
  profession,
  setProfession,
  documentTitle,
  setDocumentTitle,
  documentInputMode,
  setDocumentInputMode,
  documentText,
  setDocumentText,
  documentFileName,
  documentFileSizeBytes,
  documentUploadMaxBytes,
  documentTextLimit,
  onDocumentFileChange,
  audienceType,
  setAudienceType,
  customInstruction,
  setCustomInstruction,
  numQuestions,
  setNumQuestions,
  questionType,
  setQuestionType,
  difficultyLevel,
  setDifficultyLevel,
  token,
  setToken,
  previousToken = "",
}: QuizGenerationSectionProps & {
  token: string;
  setToken: (val: string) => void;
  previousToken?: string;
}) {
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [difficultyOpen, setDifficultyOpen] = useState(false);
  const difficultyRef = useRef<HTMLDivElement | null>(null);

  const difficultyOptions = [
    { value: "easy", label: "Easy" },
    { value: "medium", label: "Medium" },
    { value: "hard", label: "Hard" },
  ];

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) {
      return `${bytes.toLocaleString()} B`;
    }

    const units = ["KB", "MB", "GB"];
    let value = bytes / 1024;
    let unitIndex = 0;

    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }

    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  useEffect(() => {
    if (!difficultyOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        difficultyRef.current &&
        !difficultyRef.current.contains(event.target as Node)
      ) {
        setDifficultyOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [difficultyOpen]);

  return (
    <section className="w-full max-w-3xl mx-auto bg-white shadow rounded-xl px-6 py-8">
      <h2 className="text-2xl font-semibold text-[#2C3E50] mb-2">
        Generate Quiz
      </h2>
      <p className="text-sm text-gray-500 mb-8">
        Effortlessly create customized quizzes on any topic
      </p>

      <div className="mb-8">
        <RequiredLabel text="Quiz source" required />
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <button
            type="button"
            onClick={() => setGenerationMode("topic")}
            className={`rounded-xl border px-4 py-4 text-left transition ${
              generationMode === "topic"
                ? "border-[#0F2654] bg-[#0F2654] text-white"
                : "border-gray-300 bg-white text-[#2C3E50] hover:border-[#0F2654]/40"
            }`}
          >
            <span className="block text-sm font-semibold">Topic prompt</span>
            <span
              className={`mt-1 block text-xs ${
                generationMode === "topic" ? "text-white/80" : "text-gray-500"
              }`}
            >
              Generate from a concept, profession, or learning context.
            </span>
          </button>
          <button
            type="button"
            onClick={() => setGenerationMode("document")}
            className={`rounded-xl border px-4 py-4 text-left transition ${
              generationMode === "document"
                ? "border-[#0F2654] bg-[#0F2654] text-white"
                : "border-gray-300 bg-white text-[#2C3E50] hover:border-[#0F2654]/40"
            }`}
          >
            <span className="block text-sm font-semibold">
              Document or pasted text
            </span>
            <span
              className={`mt-1 block text-xs ${
                generationMode === "document"
                  ? "text-white/80"
                  : "text-gray-500"
              }`}
            >
              Upload PDF, DOCX, TXT, or paste study notes for RAG-based quiz
              generation.
            </span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="md:col-span-2">
          {generationMode === "topic" ? (
            <>
              <RequiredLabel
                text="Enter The Concept/Context For This Quiz"
                required
              />
              <input
                type="text"
                value={profession}
                onChange={(e) => setProfession(e.target.value)}
                placeholder="Enter the concept/context here"
                className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                required
              />
            </>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
                  Material title
                </label>
                <input
                  type="text"
                  value={documentTitle}
                  onChange={(event) => setDocumentTitle(event.target.value)}
                  placeholder="Optional title for this material"
                  className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-[#2C3E50] mb-2">
                  Learning material input
                </label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setDocumentInputMode("upload")}
                    className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                      documentInputMode === "upload"
                        ? "bg-[#0F2654] text-white"
                        : "bg-gray-100 text-[#2C3E50] hover:bg-gray-200"
                    }`}
                  >
                    Upload file
                  </button>
                  <button
                    type="button"
                    onClick={() => setDocumentInputMode("paste")}
                    className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                      documentInputMode === "paste"
                        ? "bg-[#0F2654] text-white"
                        : "bg-gray-100 text-[#2C3E50] hover:bg-gray-200"
                    }`}
                  >
                    Paste text
                  </button>
                </div>
              </div>

              {documentInputMode === "upload" ? (
                <div className="rounded-xl border border-dashed border-[#0F2654]/30 bg-[#f8fbff] p-5">
                  <label className="block text-sm font-semibold text-[#2C3E50] mb-2">
                    Upload PDF, DOCX, or TXT
                  </label>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(event) =>
                      onDocumentFileChange(event.target.files?.[0] || null)
                    }
                    className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-[#0F2654] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-[#0a3264]"
                  />
                  <p className="mt-3 text-xs text-gray-500">
                    Accepted range: 1 byte to{" "}
                    {documentUploadMaxBytes.toLocaleString()} bytes (
                    {formatBytes(documentUploadMaxBytes)}).
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {documentFileName
                      ? `Selected file: ${documentFileName} (${documentFileSizeBytes.toLocaleString()} bytes / ${formatBytes(documentFileSizeBytes)})`
                      : "No file selected yet."}
                  </p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
                    Paste the learning material
                  </label>
                  <textarea
                    rows={8}
                    value={documentText}
                    onChange={(event) => setDocumentText(event.target.value)}
                    maxLength={documentTextLimit}
                    placeholder="Paste lecture notes, textbook excerpts, or study material here."
                    className="w-full border border-gray-300 rounded-md px-4 py-3 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                  />
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                    <span>
                      Max {documentTextLimit.toLocaleString()} characters for
                      pasted material.
                    </span>
                    <span
                      className={
                        documentText.length >= documentTextLimit * 0.9
                          ? "font-semibold text-[#0F2654]"
                          : ""
                      }
                    >
                      {documentText.length.toLocaleString()} /{" "}
                      {documentTextLimit.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
                  Focus area in this material (optional)
                </label>
                <input
                  type="text"
                  value={profession}
                  onChange={(e) => setProfession(e.target.value)}
                  placeholder="Example: chapter 3 definitions or respiratory system"
                  className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Leave blank to generate from the most central ideas in the
                  material.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="md:col-span-2 relative">
          <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
            API Token (Optional)
          </label>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onFocus={() => setShowSuggestion(true)}
            onBlur={() => setTimeout(() => setShowSuggestion(false), 150)}
            placeholder="Enter your API token"
            className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
          />
          {showSuggestion && previousToken && (
            <div
              className="absolute w-full mt-1 bg-white border rounded-md shadow z-10 cursor-pointer"
              onMouseDown={() => {
                setToken(previousToken);
                setShowSuggestion(false);
              }}
            >
              <div className="px-4 py-2 hover:bg-gray-100">
                <p className="text-xs text-gray-500">
                  Use previously saved token
                </p>
                <p className="text-sm text-gray-700">{previousToken}</p>
              </div>
            </div>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Leave blank to use the default server API key.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              Audience type
            </label>
            <input
              type="text"
              value={audienceType}
              onChange={(e) => setAudienceType(e.target.value)}
              placeholder="Audience"
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              Select difficulty level
            </label>
            <div className="relative" ref={difficultyRef}>
              <button
                type="button"
                onClick={() => setDifficultyOpen((prev) => !prev)}
                className="w-full border border-gray-300 rounded-md px-4 py-2 text-left bg-white text-[#2C3E50] focus:outline-none focus:ring focus:ring-blue-500 flex items-center justify-between"
                aria-haspopup="listbox"
                aria-expanded={difficultyOpen}
              >
                <span>
                  {
                    difficultyOptions.find(
                      (option) => option.value === difficultyLevel,
                    )?.label
                  }
                </span>
                <svg
                  className={`h-4 w-4 text-[#0F2654] transition-transform ${
                    difficultyOpen ? "rotate-180" : ""
                  }`}
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
              {difficultyOpen && (
                <div
                  className="absolute left-0 right-0 mt-1 rounded-md border border-[#0F2654]/20 bg-white shadow-lg z-20"
                  role="listbox"
                >
                  {difficultyOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      role="option"
                      aria-selected={option.value === difficultyLevel}
                      onClick={() => {
                        setDifficultyLevel(option.value);
                        setDifficultyOpen(false);
                      }}
                      className={`w-full px-4 py-2 text-left text-sm ${
                        option.value === difficultyLevel
                          ? "bg-[#0F2654] text-white"
                          : "text-[#2C3E50] hover:bg-[#0F2654]/10"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              Custom instruction
            </label>
            <textarea
              rows={3}
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder="Add specific instruction"
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
            {generationMode === "document" && (
              <p className="mt-1 text-xs text-gray-500">
                The backend uses RAG retrieval first, then generates questions
                only from the retrieved document chunks.
              </p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <RequiredLabel text="Question type(s)" required />
            <div className="space-y-2">
              {QUESTION_TYPES.map((type) => (
                <label
                  key={type.value}
                  className={`flex items-center px-4 py-2 border rounded-md cursor-pointer ${
                    questionType === type.value
                      ? "border-blue-600 bg-blue-50"
                      : "border-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    value={type.value}
                    checked={questionType === type.value}
                    onChange={() => setQuestionType(type.value)}
                    className="mr-2 accent-blue-600"
                  />
                  <span className="text-gray-700 text-sm">{type.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <RequiredLabel text="Number of questions" required />
            <input
              type="number"
              value={numQuestions}
              onChange={(e) =>
                setNumQuestions(
                  Math.min(10, Math.max(1, Number(e.target.value))),
                )
              }
              placeholder="Number of questions"
              min={1}
              max={10}
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
