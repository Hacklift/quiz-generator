"use client";

import React, { useMemo, useState } from "react";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";
import { useAuth } from "../../contexts/authContext";
import SignInModal from "../../components/auth/SignInModal";

const POPULAR_CATEGORIES = [
  {
    id: "mathematics",
    title: "Mathematics",
    description: "Algebra, geometry, calculus, and number theory.",
    tags: ["Algebra", "Geometry", "Calculus"],
    quizzes: [
      { title: "Algebra Essentials", questions: 15, difficulty: "Beginner" },
      {
        title: "Geometry in Real Life",
        questions: 12,
        difficulty: "Intermediate",
      },
      { title: "Calculus Snapshots", questions: 10, difficulty: "Advanced" },
    ],
  },
  {
    id: "technology",
    title: "Technology",
    description: "Programming, AI, cybersecurity, and modern tools.",
    tags: ["Programming", "AI", "Security"],
    quizzes: [
      { title: "Frontend Fundamentals", questions: 14, difficulty: "Beginner" },
      { title: "AI Concepts Check", questions: 12, difficulty: "Intermediate" },
      { title: "Cybersecurity Basics", questions: 10, difficulty: "Beginner" },
    ],
  },
  {
    id: "english",
    title: "English",
    description: "Grammar, vocabulary, literature, and writing.",
    tags: ["Grammar", "Vocabulary", "Literature"],
    quizzes: [
      { title: "Grammar Repair Kit", questions: 12, difficulty: "Beginner" },
      {
        title: "Vocabulary Builder",
        questions: 15,
        difficulty: "Intermediate",
      },
      { title: "Literary Classics", questions: 10, difficulty: "Advanced" },
    ],
  },
  {
    id: "history",
    title: "History",
    description: "World history, civilizations, and key events.",
    tags: ["World", "Civilizations", "Events"],
    quizzes: [
      { title: "Ancient Civilizations", questions: 12, difficulty: "Beginner" },
      {
        title: "Revolutions & Change",
        questions: 14,
        difficulty: "Intermediate",
      },
      {
        title: "Modern History Sprint",
        questions: 10,
        difficulty: "Intermediate",
      },
    ],
  },
  {
    id: "science",
    title: "Science",
    description: "Physics, chemistry, biology, and earth science.",
    tags: ["Physics", "Chemistry", "Biology"],
    quizzes: [
      { title: "Physics in Motion", questions: 12, difficulty: "Intermediate" },
      { title: "Chemistry Foundations", questions: 15, difficulty: "Beginner" },
      { title: "Biology Essentials", questions: 12, difficulty: "Beginner" },
    ],
  },
  {
    id: "business",
    title: "Business",
    description: "Leadership, finance, marketing, and strategy.",
    tags: ["Leadership", "Finance", "Marketing"],
    quizzes: [
      { title: "Business Basics", questions: 12, difficulty: "Beginner" },
      {
        title: "Marketing Strategy",
        questions: 10,
        difficulty: "Intermediate",
      },
      {
        title: "Finance Fundamentals",
        questions: 14,
        difficulty: "Intermediate",
      },
    ],
  },
  {
    id: "art-design",
    title: "Art & Design",
    description: "Design principles, art history, and creativity.",
    tags: ["Design", "Art History", "Creativity"],
    quizzes: [
      { title: "Design Principles", questions: 10, difficulty: "Beginner" },
      {
        title: "Art History Highlights",
        questions: 12,
        difficulty: "Intermediate",
      },
      { title: "Creative Thinking", questions: 8, difficulty: "Beginner" },
    ],
  },
  {
    id: "geography",
    title: "Geography",
    description: "Maps, regions, cultures, and landmarks.",
    tags: ["Maps", "Regions", "Landmarks"],
    quizzes: [
      { title: "World Maps", questions: 12, difficulty: "Beginner" },
      {
        title: "Capitals & Countries",
        questions: 15,
        difficulty: "Intermediate",
      },
      {
        title: "Physical Geography",
        questions: 10,
        difficulty: "Intermediate",
      },
    ],
  },
  {
    id: "language",
    title: "Languages",
    description: "Spanish, French, and multilingual practice.",
    tags: ["Spanish", "French", "General"],
    quizzes: [
      { title: "Spanish Basics", questions: 12, difficulty: "Beginner" },
      { title: "French Vocabulary", questions: 10, difficulty: "Beginner" },
      { title: "Language Patterns", questions: 12, difficulty: "Intermediate" },
    ],
  },
  {
    id: "health",
    title: "Health & Wellness",
    description: "Nutrition, fitness, mental health, and wellbeing.",
    tags: ["Nutrition", "Fitness", "Wellness"],
    quizzes: [
      { title: "Nutrition Basics", questions: 10, difficulty: "Beginner" },
      { title: "Fitness Fundamentals", questions: 12, difficulty: "Beginner" },
      { title: "Mindfulness Check", questions: 8, difficulty: "Beginner" },
    ],
  },
];

export default function PopularQuizzesPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [searchTerm, setSearchTerm] = useState("");

  const filteredCategories = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return POPULAR_CATEGORIES;

    return POPULAR_CATEGORIES.filter((category) => {
      const inTitle = category.title.toLowerCase().includes(term);
      const inTags = category.tags.some((tag) =>
        tag.toLowerCase().includes(term),
      );
      const inDescription = category.description.toLowerCase().includes(term);
      return inTitle || inTags || inDescription;
    });
  }, [searchTerm]);

  const selectedCategory = POPULAR_CATEGORIES.find(
    (category) => category.id === selectedCategoryId,
  );

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
      </div>
    );
  }

  if (!isAuthenticated && !isLoading) {
    return (
      <div className="flex flex-col min-h-screen bg-gray-100">
        <NavBar />

        <main className="flex-1 px-4 sm:px-6 md:px-8 py-10">
          <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-md border border-gray-200 p-8 text-center">
            <h1 className="text-2xl sm:text-3xl font-bold text-[#0F2654]">
              Popular Quizzes
            </h1>
            <p className="text-gray-600 mt-3">
              This page is available to signed-in users. Please{" "}
              <span
                onClick={() => setIsLoginOpen(true)}
                className="text-blue-600 underline cursor-pointer"
              >
                sign in
              </span>{" "}
              to explore popular quizzes by category.
            </p>
          </div>
        </main>

        <Footer />

        <SignInModal
          isOpen={isLoginOpen}
          onClose={() => setIsLoginOpen(false)}
          switchToSignUp={() => {}}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-6xl mx-auto space-y-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-widest text-[#0F2654]/70">
                Discover what learners love
              </p>
              <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
                Popular Quizzes
              </h1>
              <p className="text-gray-600 mt-2 max-w-2xl">
                Browse top quizzes by field and open a category to explore what
                is trending.
              </p>
            </div>

            <div className="w-full md:w-80">
              <label className="text-xs text-gray-500 font-medium">
                Search categories
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Try Mathematics, AI, Grammar..."
                className="mt-1 w-full rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2654]/30"
              />
            </div>
          </header>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCategories.map((category) => {
              const isSelected = category.id === selectedCategoryId;
              return (
                <div
                  key={category.id}
                  className={`bg-white rounded-2xl border shadow-sm p-5 flex flex-col gap-4 transition-all ${
                    isSelected
                      ? "border-[#0F2654] shadow-md"
                      : "border-gray-200"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-[#0F2654]">
                        {category.title}
                      </h2>
                      <p className="text-sm text-gray-600 mt-1">
                        {category.description}
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-[#0F2654] bg-[#0F2654]/10 px-2 py-1 rounded-full">
                      {category.quizzes.length} quizzes
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {category.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  <button
                    onClick={() =>
                      setSelectedCategoryId(isSelected ? null : category.id)
                    }
                    className={`mt-auto w-full rounded-xl py-2 text-sm font-semibold transition-colors ${
                      isSelected
                        ? "bg-[#0F2654] text-white"
                        : "bg-[#0F2654]/10 text-[#0F2654] hover:bg-[#0F2654]/20"
                    }`}
                  >
                    {isSelected ? "Close" : "Open"}
                  </button>
                </div>
              );
            })}
          </div>

          {filteredCategories.length === 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-600">
              No categories matched your search. Try a different keyword.
            </div>
          )}

          {selectedCategory && (
            <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h2 className="text-2xl font-bold text-[#0F2654]">
                    Popular in {selectedCategory.title}
                  </h2>
                  <p className="text-sm text-gray-600">
                    Top picks curated for this field.
                  </p>
                </div>
                <span className="text-xs uppercase tracking-widest text-gray-400">
                  Updated weekly
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {selectedCategory.quizzes.map((quiz) => (
                  <div
                    key={quiz.title}
                    className="border border-gray-200 rounded-xl p-4 flex flex-col gap-2"
                  >
                    <h3 className="font-semibold text-[#0F2654]">
                      {quiz.title}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {quiz.questions} questions • {quiz.difficulty}
                    </p>
                    <span className="text-xs uppercase tracking-widest text-gray-400">
                      Preview
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="text-xs text-gray-500">
            New categories are added regularly. If you want a specific field,
            request it from the sidebar feedback form.
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
