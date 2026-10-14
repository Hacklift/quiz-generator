"use client";
import { useTranslation } from "react-i18next";

import React, { useMemo, useState } from "react";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";

type TimeRange = "today" | "week" | "month" | "all";

const categories = [
  "All Categories",
  "Science",
  "Arts",
  "Technology",
  "History",
  "Business",
  "Health",
  "Education",
];

const difficulties = ["All Levels", "Easy", "Medium", "Hard"];
const questionTypes = ["All Types", "multichoice", "true-false", "open-ended"];
const sorts = ["Most Popular", "Most Saves", "Highest Rated", "Newest"];

const timeRangeToDays = (range: TimeRange) => {
  if (range === "today") return 1;
  if (range === "week") return 7;
  if (range === "month") return 30;
  return Number.POSITIVE_INFINITY;
};

type SelectOption = string;

function FilterSelect({
  label,
  value,
  options,
  onChange,
  isOpen,
  onToggle,
}: {
  label: string;
  value: SelectOption;
  options: SelectOption[];
  onChange: (value: SelectOption) => void;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="relative">
      <label className="text-xs uppercase tracking-wide text-gray-500">
        {label}
      </label>
      <button
        type="button"
        onClick={onToggle}
        className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 bg-white text-left flex items-center justify-between"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="text-sm text-[#0F2654]">{value}</span>
        <span className="text-[#0F2654]">▾</span>
      </button>
      {isOpen && (
        <div
          className="absolute z-20 mt-2 w-full rounded-lg border border-[#d5dbe3] bg-[#f2f6ff] shadow-lg"
          role="listbox"
        >
          {options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                onChange(option);
                onToggle();
              }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-[#0F2654] hover:text-white transition ${
                option === value
                  ? "font-semibold text-[#0F2654]"
                  : "text-[#1f2a44]"
              }`}
              role="option"
              aria-selected={option === value}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PopularQuizzesPage() {
  const { t: uiText } = useTranslation("ui");

  const mockPopularQuizzes = [
    {
      id: "pq-1",
      title: uiText("m3af918d958c3e5ed"),
      category: "Science",
      difficulty: "Easy",
      questionType: "multichoice",
      plays: 1240,
      saves: 310,
      rating: 4.8,
      lastActiveDays: 1,
    },
    {
      id: "pq-2",
      title: uiText("mecfc250397ce7aee"),
      category: "Arts",
      difficulty: "Medium",
      questionType: "open-ended",
      plays: 860,
      saves: 190,
      rating: 4.6,
      lastActiveDays: 3,
    },
    {
      id: "pq-3",
      title: uiText("m27247da599aadeb1"),
      category: "Technology",
      difficulty: "Medium",
      questionType: "multichoice",
      plays: 2140,
      saves: 540,
      rating: 4.9,
      lastActiveDays: 2,
    },
    {
      id: "pq-4",
      title: uiText("m900158083571794b"),
      category: "History",
      difficulty: "Easy",
      questionType: "true-false",
      plays: 990,
      saves: 210,
      rating: 4.5,
      lastActiveDays: 8,
    },
    {
      id: "pq-5",
      title: uiText("m5b09c4815d41a326"),
      category: "Business",
      difficulty: "Hard",
      questionType: "open-ended",
      plays: 620,
      saves: 160,
      rating: 4.3,
      lastActiveDays: 12,
    },
    {
      id: "pq-6",
      title: uiText("m48f749ce8951339c"),
      category: "Health",
      difficulty: "Easy",
      questionType: "multichoice",
      plays: 1120,
      saves: 280,
      rating: 4.7,
      lastActiveDays: 6,
    },
    {
      id: "pq-7",
      title: uiText("m2635645b424541ad"),
      category: "Education",
      difficulty: "Medium",
      questionType: "true-false",
      plays: 700,
      saves: 140,
      rating: 4.4,
      lastActiveDays: 16,
    },
    {
      id: "pq-8",
      title: uiText("ma279e3fe3de341c0"),
      category: "Technology",
      difficulty: "Hard",
      questionType: "open-ended",
      plays: 1580,
      saves: 420,
      rating: 4.8,
      lastActiveDays: 5,
    },
  ];

  const timeRanges: { key: TimeRange; label: string; hint: string }[] = [
    { key: "today", label: uiText("m2b065c7c9ce466e5"), hint: "Last 24 hours" },
    { key: "week", label: uiText("m017cb5682cc32316"), hint: "Last 7 days" },
    { key: "month", label: uiText("m64367736022306e3"), hint: "Last 30 days" },
    { key: "all", label: uiText("m476adfac4cd9494e"), hint: "All activity" },
  ];

  const [range, setRange] = useState<TimeRange>("week");
  const [category, setCategory] = useState("All Categories");
  const [difficulty, setDifficulty] = useState("All Levels");
  const [questionType, setQuestionType] = useState("All Types");
  const [sort, setSort] = useState("Most Popular");
  const [query, setQuery] = useState("");
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const daysLimit = timeRangeToDays(range);
    let result = mockPopularQuizzes.filter((quiz) => {
      if (quiz.lastActiveDays > daysLimit) return false;
      if (category !== "All Categories" && quiz.category !== category)
        return false;
      if (difficulty !== "All Levels" && quiz.difficulty !== difficulty)
        return false;
      if (questionType !== "All Types" && quiz.questionType !== questionType)
        return false;
      if (query.trim()) {
        const q = query.trim().toLowerCase();
        if (
          !quiz.title.toLowerCase().includes(q) &&
          !quiz.category.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });

    if (sort === "Most Popular") {
      result = result.sort((a, b) => b.plays - a.plays);
    } else if (sort === "Most Saves") {
      result = result.sort((a, b) => b.saves - a.saves);
    } else if (sort === "Highest Rated") {
      result = result.sort((a, b) => b.rating - a.rating);
    } else if (sort === "Newest") {
      result = result.sort((a, b) => a.lastActiveDays - b.lastActiveDays);
    }

    return result;
  }, [range, category, difficulty, questionType, sort, query]);

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="flex flex-col gap-3">
            <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
              {uiText("m546ddeb74ccc707a")}
            </h1>
            <p className="text-gray-600 max-w-3xl">
              {uiText("m72c294627434ab04")}
            </p>
          </div>

          <section className="bg-white p-4 sm:p-6 rounded-2xl shadow-md border border-gray-200">
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                {timeRanges.map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setRange(item.key)}
                    className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                      range === item.key
                        ? "bg-[#0F2654] text-white border-[#0F2654]"
                        : "bg-white text-[#0F2654] border-[#d5dbe3] hover:bg-[#f2f6ff]"
                    }`}
                    title={item.hint}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <FilterSelect
                  label={uiText("m292c06f0045a45d0")}
                  value={category}
                  options={categories}
                  onChange={setCategory}
                  isOpen={openDropdown === "category"}
                  onToggle={() =>
                    setOpenDropdown(
                      openDropdown === "category" ? null : "category",
                    )
                  }
                />
                <FilterSelect
                  label={uiText("mbe44133ed57f9e44")}
                  value={difficulty}
                  options={difficulties}
                  onChange={setDifficulty}
                  isOpen={openDropdown === "difficulty"}
                  onToggle={() =>
                    setOpenDropdown(
                      openDropdown === "difficulty" ? null : "difficulty",
                    )
                  }
                />
                <FilterSelect
                  label={uiText("mcb38ff91243be92f")}
                  value={questionType}
                  options={questionTypes}
                  onChange={setQuestionType}
                  isOpen={openDropdown === "questionType"}
                  onToggle={() =>
                    setOpenDropdown(
                      openDropdown === "questionType" ? null : "questionType",
                    )
                  }
                />
                <FilterSelect
                  label={uiText("m6d2227555fccff99")}
                  value={sort}
                  options={sorts}
                  onChange={setSort}
                  isOpen={openDropdown === "sort"}
                  onToggle={() =>
                    setOpenDropdown(openDropdown === "sort" ? null : "sort")
                  }
                />
              </div>

              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <input
                  type="search"
                  placeholder={uiText("m05845c469c45d10f")}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full md:flex-1 border border-gray-300 rounded-lg px-3 py-2 bg-white"
                />
                <button
                  onClick={() => {
                    setQuery("");
                    setCategory("All Categories");
                    setDifficulty("All Levels");
                    setQuestionType("All Types");
                    setSort("Most Popular");
                    setRange("week");
                  }}
                  className="md:w-auto px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100"
                >
                  {uiText("m660f3d76f4f2802d")}
                </button>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filtered.map((quiz) => (
              <div
                key={quiz.id}
                className="bg-white rounded-2xl shadow-md border border-gray-200 p-6 flex flex-col gap-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[#6b7280]">
                      {quiz.category}
                    </p>
                    <h2 className="text-xl font-semibold text-[#0F2654]">
                      {quiz.title}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {quiz.questionType} · {quiz.difficulty}
                    </p>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full bg-[#f2f6ff] text-[#0F2654] font-semibold">
                    {uiText("m92340695899bd2d8")}
                    {quiz.lastActiveDays}
                    {uiText("m738bb7160d3b2cec")}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <p className="text-xs text-gray-500">
                      {uiText("m725b66fb9f520d78")}
                    </p>
                    <p className="text-lg font-semibold text-[#0F2654]">
                      {quiz.plays}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <p className="text-xs text-gray-500">
                      {uiText("m989716267f5c4d56")}
                    </p>
                    <p className="text-lg font-semibold text-[#0F2654]">
                      {quiz.saves}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <p className="text-xs text-gray-500">
                      {uiText("m9f29530464f730bd")}
                    </p>
                    <p className="text-lg font-semibold text-[#0F2654]">
                      {quiz.rating}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-full bg-[#e8f0ff] text-[#0F2654] font-medium">
                    {uiText("m5e1a0ebc939d884a")}
                  </span>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-[#f6f6f6] text-gray-700 font-medium">
                    {uiText("m2cb59542c1d87000")}
                  </span>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <button className="flex-1 px-4 py-2 rounded-lg bg-[#0F2654] text-white font-semibold hover:bg-[#173773]">
                    {uiText("m515f6a0d4288e0d7")}
                  </button>
                  <button className="flex-1 px-4 py-2 rounded-lg border border-[#0F2654] text-[#0F2654] font-semibold hover:bg-[#f2f6ff]">
                    {uiText("m1a720e27caa63948")}
                  </button>
                </div>
              </div>
            ))}
          </section>

          {filtered.length === 0 && (
            <div className="bg-white rounded-2xl p-8 border border-gray-200 text-center text-gray-600">
              {uiText("m8b4fc64d9f49d86e")}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
