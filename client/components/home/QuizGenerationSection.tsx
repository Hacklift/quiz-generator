import { QuizGenerationSectionProps } from "../../interfaces/props";
import RequiredLabel from "./common/RequiredLabel";

const QUESTION_TYPES = [
  { label: "Multiple Choice", value: "multichoice" },
  { label: "True/False", value: "true-false" },
  { label: "Short Answer", value: "short-answer" },
  { label: "Open Ended", value: "open-ended" },
];

export default function QuizGenerationSection({
  profession,
  setProfession,
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
}: QuizGenerationSectionProps & {
  token: string;
  setToken: (val: string) => void;
}) {
  return (
    <section className="w-full max-w-3xl mx-auto bg-white shadow rounded-xl px-6 py-8">
      <h2 className="text-2xl font-semibold text-[#2C3E50] mb-2">
        Generate Quiz
      </h2>
      <p className="text-sm text-gray-500 mb-8">
        Effortlessly create customized quizzes on any topic
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Quiz Topic */}
        <div className="md:col-span-2">
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
        </div>

        {/* Optional API Token */}
        <div className="md:col-span-2">
          <label className="block text-sm font-semibold text-[#2C3E50] mb-1">
            API Token (Optional)
          </label>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter your API token (optional)"
            className="w-full border border-gray-300 rounded-md px-4 py-2 placeholder-gray-400 focus:outline-none focus:ring focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Leave blank to use the default server API key.
          </p>
        </div>

        {/* Left Column: Audience Type, Difficulty Level, Custom Instruction */}
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
            <select
              value={difficultyLevel}
              onChange={(e) => setDifficultyLevel(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring focus:ring-blue-500"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
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
          </div>
        </div>

        {/* Right Column: Question Type and Number of Questions */}
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
