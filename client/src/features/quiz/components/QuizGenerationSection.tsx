import { useTranslation } from "react-i18next";
import { useEffect, useRef, useState } from "react";
import { QuizGenerationSectionProps } from "@shared/types/props";
import RequiredLabel from "./common/RequiredLabel";

const QUIZ_GENERATION_MAX_QUESTIONS = Number(
  process.env.NEXT_PUBLIC_QUIZ_GENERATION_MAX_QUESTIONS || 10,
);

export default function QuizGenerationSection({
  generationMode,
  setGenerationMode,
  profession,
  setProfession,
  professionPlaceholder = "Enter the concept/context here",
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
  showTokenInput = true,
}: QuizGenerationSectionProps & {
  token: string;
  setToken: (val: string) => void;
  previousToken?: string;
  showTokenInput?: boolean;
}) {
  const { t: uiText } = useTranslation("ui");

  const QUESTION_TYPES = [
    { label: uiText("m987caef59af796c7"), value: "multichoice" },
    { label: uiText("m3d971996ecec47b9"), value: "true-false" },
    { label: uiText("m91b03d90535d804c"), value: "short-answer" },
    { label: uiText("mfbea5ba076ee9152"), value: "open-ended" },
  ];

  const [showSuggestion, setShowSuggestion] = useState(false);
  const [difficultyOpen, setDifficultyOpen] = useState(false);
  const difficultyRef = useRef<HTMLDivElement | null>(null);

  const difficultyOptions = [
    { value: "easy", label: uiText("md6915875decb6e43") },
    { value: "medium", label: uiText("m8e588cd187741f1c") },
    { value: "hard", label: uiText("m9e73f8fa9cb76c44") },
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
        {uiText("m5da69270e5973c17")}
      </h2>
      <p className="text-sm text-gray-500 mb-8">
        {uiText("m6fe47ccceda6ec3d")}
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
            <span className="block text-sm font-semibold">
              {uiText("mad3d6c55ff5304dd")}
            </span>
            <span
              className={`mt-1 block text-xs ${
                generationMode === "topic" ? "text-white/80" : "text-gray-500"
              }`}
            >
              {uiText("m829ee8b0f2ebe54b")}
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
              {uiText("mc55b2768bbf36dbc")}
            </span>
            <span
              className={`mt-1 block text-xs ${
                generationMode === "document"
                  ? "text-white/80"
                  : "text-gray-500"
              }`}
            >
              {uiText("ma11570acd2a57311")}
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
                placeholder={professionPlaceholder}
                className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                required
              />
            </>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
                  {uiText("mf5e2ce5b03c3702c")}
                </label>
                <input
                  type="text"
                  value={documentTitle}
                  onChange={(event) => setDocumentTitle(event.target.value)}
                  placeholder={uiText("m9c465613449fb3a8")}
                  className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-[#2C3E50] mb-2">
                  {uiText("m1de62c92c10ab9f5")}
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
                    {uiText("md99bcd78b586826a")}
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
                    {uiText("m9328724b4cf1557b")}
                  </button>
                </div>
              </div>

              {documentInputMode === "upload" ? (
                <div className="rounded-xl border border-dashed border-[#0F2654]/30 bg-[#f8fbff] p-5">
                  <label className="block text-sm font-semibold text-[#2C3E50] mb-2">
                    {uiText("m1d6fb8d10a82b6b0")}
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
                    {uiText("m240dde20dd3976b1", {
                      value0: documentUploadMaxBytes.toLocaleString(),
                      value1: formatBytes(documentUploadMaxBytes),
                    })}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {documentFileName
                      ? uiText("m2d564fc57fa60a92", {
                          value0: documentFileName,
                          value1: documentFileSizeBytes.toLocaleString(),
                          value2: formatBytes(documentFileSizeBytes),
                        })
                      : uiText("medeb5926f8115ab1")}
                  </p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
                    {uiText("mefbcbd3468f628cd")}
                  </label>
                  <textarea
                    rows={8}
                    value={documentText}
                    onChange={(event) => setDocumentText(event.target.value)}
                    maxLength={documentTextLimit}
                    placeholder={uiText("m379e9c08827781ad")}
                    className="w-full border border-gray-300 rounded-md px-4 py-3 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                  />
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                    <span>
                      {uiText("mb3e9ed39ed208a66", {
                        value0: documentTextLimit.toLocaleString(),
                      })}
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
                  {uiText("m0a29ef02931121f6")}
                </label>
                <input
                  type="text"
                  value={profession}
                  onChange={(e) => setProfession(e.target.value)}
                  placeholder={uiText("m3f5aeb7abf596752")}
                  className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  {uiText("mda5fb0acd70e0452")}
                </p>
              </div>
            </div>
          )}
        </div>

        {showTokenInput && (
          <div className="md:col-span-2 relative">
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              {uiText("m52e85ebf5fc86938")}
            </label>
            <input
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onFocus={() => setShowSuggestion(true)}
              onBlur={() => setTimeout(() => setShowSuggestion(false), 150)}
              placeholder={uiText("maf61075931655199")}
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
                    {uiText("m488bf65bb224734c")}
                  </p>
                  <p className="text-sm text-gray-700">{previousToken}</p>
                </div>
              </div>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {uiText("md1ea04648b55a84b")}
            </p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              {uiText("mb9f830f1e015527b")}
            </label>
            <input
              type="text"
              value={audienceType}
              onChange={(e) => setAudienceType(e.target.value)}
              placeholder={uiText("m545c02357695a6ff")}
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
              {uiText("m59bb1df0ef048050")}
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
              {uiText("m8ff736eb8406612e")}
            </label>
            <textarea
              rows={3}
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              placeholder={uiText("m46c3614819d1ccda")}
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
            {generationMode === "document" && (
              <p className="mt-1 text-xs text-gray-500">
                {uiText("m682291948542e96e")}
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
                  Math.min(
                    QUIZ_GENERATION_MAX_QUESTIONS,
                    Math.max(1, Number(e.target.value)),
                  ),
                )
              }
              placeholder={uiText("m4bbde39fcd87f7de")}
              min={1}
              max={QUIZ_GENERATION_MAX_QUESTIONS}
              className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
