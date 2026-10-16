"use client";
import { useTranslation } from "react-i18next";

import Link from "next/link";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { usePersona } from "@features/persona/context/personaContext";
import { getCategories } from "@features/categories/api/categoriesApi";

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

export default function CategoriesPage() {
  const { t: uiText } = useTranslation("ui");

  const { category, isLoading: personaLoading } = usePersona();
  const [showAll, setShowAll] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (personaLoading) return;
    let cancelled = false;
    const loadCategories = async () => {
      setIsLoading(true);
      try {
        const filter = showAll ? undefined : (category ?? undefined);
        const result = await getCategories(filter);
        if (!cancelled) {
          setCategories(result);
        }
      } catch (error) {
        if (!cancelled) {
          console.error(error);
          toast.error(uiText("mf0dc38ac2b15faa5"));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    loadCategories();
    return () => {
      cancelled = true;
    };
  }, [category, showAll, personaLoading]);
  return (
    <div className="flex min-h-screen flex-col bg-white text-[#0F2654]">
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-grow px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
              {uiText("m64af555237039009")}
            </p>
            <h1 className="mt-2 text-3xl font-bold">
              {uiText("mb8b1d894c6837252")}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              {uiText("m321edf3fd12c7436")}
            </p>
          </div>

          {category && (
            <button
              type="button"
              onClick={() => setShowAll((prev) => !prev)}
              className="rounded-full border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50"
            >
              {showAll
                ? uiText("m7edf38bf075109b9")
                : uiText("m4bf744741ec59c48")}
            </button>
          )}
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">
            {uiText("md3cf16ece0883bf2")}
          </p>
        ) : categories.length === 0 ? (
          <p className="text-sm text-slate-500">
            {uiText("m697c80be92edf491")}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((categoryName) => (
              <Link
                key={categoryName}
                href={`/categories/${slugify(categoryName)}`}
                className="rounded-2xl border border-blue-100 bg-blue-50 p-5 transition hover:border-blue-300 hover:bg-blue-100"
              >
                <h2 className="text-lg font-semibold">{categoryName}</h2>
                <p className="mt-2 text-sm text-slate-600">
                  {uiText("mba59bfcf48bd1e52")}
                </p>
              </Link>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
