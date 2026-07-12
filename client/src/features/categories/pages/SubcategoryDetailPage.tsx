"use client";

import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import {
  CategoryQuestion,
  getCategoryQuestions,
  getCategoryQuizTypes,
} from "@features/categories/api/categoriesApi";

const titleize = (value: string) =>
  value
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

export default function SubcategoryDetailPage() {
  const router = useRouter();
  const categorySlug =
    typeof router.query.categorySlug === "string"
      ? router.query.categorySlug
      : "";
  const subcategorySlug =
    typeof router.query.subcategorySlug === "string"
      ? router.query.subcategorySlug
      : "";
  const queryType =
    typeof router.query.type === "string" ? router.query.type : "";
  const pageQuery =
    typeof router.query.page === "string" ? Number(router.query.page) : 1;
  const page = Number.isFinite(pageQuery) && pageQuery > 0 ? pageQuery : 1;
  const categoryLabel = useMemo(() => titleize(categorySlug), [categorySlug]);
  const subcategoryLabel = useMemo(
    () => titleize(subcategorySlug),
    [subcategorySlug],
  );
  const [quizTypes, setQuizTypes] = useState<string[]>([]);
  const [questions, setQuestions] = useState<CategoryQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const activeType = queryType || quizTypes[0] || "";

  useEffect(() => {
    if (!categorySlug || !subcategorySlug) return;
    const loadQuizTypes = async () => {
      try {
        const types = await getCategoryQuizTypes(categorySlug, subcategorySlug);
        setQuizTypes(types);
      } catch (error) {
        console.error(error);
        toast.error("Failed to load quiz types.");
      }
    };
    loadQuizTypes();
  }, [categorySlug, subcategorySlug]);

  useEffect(() => {
    if (!categorySlug || !subcategorySlug || !activeType) {
      setIsLoading(false);
      return;
    }
    const loadQuestions = async () => {
      setIsLoading(true);
      try {
        setQuestions(
          await getCategoryQuestions({
            category: categorySlug,
            subcategory: subcategorySlug,
            questionType: activeType,
            page,
          }),
        );
      } catch (error) {
        console.error(error);
        toast.error("Failed to load category questions.");
      } finally {
        setIsLoading(false);
      }
    };
    loadQuestions();
  }, [activeType, categorySlug, page, subcategorySlug]);

  const updateType = (type: string) => {
    router.push(
      {
        pathname: `/categories/${categorySlug}/${subcategorySlug}`,
        query: { type, page: 1 },
      },
      undefined,
      { shallow: true },
    );
  };

  const updatePage = (nextPage: number) => {
    router.push(
      {
        pathname: `/categories/${categorySlug}/${subcategorySlug}`,
        query: { type: activeType, page: nextPage },
      },
      undefined,
      { shallow: true },
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-white text-[#0F2654]">
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-grow px-6 py-10">
        <Link
          href={`/categories/${encodeURIComponent(categorySlug)}`}
          className="text-sm font-semibold text-blue-700 hover:text-blue-900"
        >
          Back to {categoryLabel}
        </Link>
        <div className="mb-8 mt-4">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
            {categoryLabel}
          </p>
          <h1 className="mt-2 text-3xl font-bold">{subcategoryLabel}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Browse available questions by quiz type.
          </p>
        </div>

        {quizTypes.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            {quizTypes.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => updateType(type)}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  activeType === type
                    ? "bg-[#0F2654] text-white"
                    : "bg-blue-50 text-blue-900 hover:bg-blue-100"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading questions...</p>
        ) : questions.length === 0 ? (
          <p className="text-sm text-slate-500">
            No questions are available for this selection.
          </p>
        ) : (
          <div className="space-y-4">
            {questions.map((question, index) => (
              <article
                key={`${question.question}-${index}`}
                className="rounded-2xl border border-blue-100 bg-blue-50 p-5"
              >
                <h2 className="font-semibold">{question.question}</h2>
                {Array.isArray(question.options) &&
                  question.options.length > 0 && (
                    <ul className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                      {question.options.map((option) => (
                        <li
                          key={option}
                          className="rounded-xl bg-white px-3 py-2"
                        >
                          {option}
                        </li>
                      ))}
                    </ul>
                  )}
              </article>
            ))}
            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => updatePage(page - 1)}
                className="rounded-xl border border-blue-100 px-4 py-2 text-sm font-semibold text-blue-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">Page {page}</span>
              <button
                type="button"
                disabled={questions.length < 10}
                onClick={() => updatePage(page + 1)}
                className="rounded-xl border border-blue-100 px-4 py-2 text-sm font-semibold text-blue-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
