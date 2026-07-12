"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { getCategories } from "@features/categories/api/categoriesApi";

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

export default function CategoriesPage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        setCategories(await getCategories());
      } catch (error) {
        console.error(error);
        toast.error("Failed to load categories.");
      } finally {
        setIsLoading(false);
      }
    };
    loadCategories();
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-white text-[#0F2654]">
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-grow px-6 py-10">
        <div className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
            Browse quizzes
          </p>
          <h1 className="mt-2 text-3xl font-bold">Categories</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Explore curated quiz questions by category and subcategory.
          </p>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading categories...</p>
        ) : categories.length === 0 ? (
          <p className="text-sm text-slate-500">
            No categories are available yet.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((category) => (
              <Link
                key={category}
                href={`/categories/${slugify(category)}`}
                className="rounded-2xl border border-blue-100 bg-blue-50 p-5 transition hover:border-blue-300 hover:bg-blue-100"
              >
                <h2 className="text-lg font-semibold">{category}</h2>
                <p className="mt-2 text-sm text-slate-600">
                  View subcategories and quiz types.
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
