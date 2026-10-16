"use client";
import { useTranslation } from "react-i18next";

import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { getSubcategories } from "@features/categories/api/categoriesApi";

const titleize = (value: string) =>
  value
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

export default function CategoryDetailPage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const categorySlug =
    typeof router.query.categorySlug === "string"
      ? router.query.categorySlug
      : "";
  const categoryLabel = useMemo(() => titleize(categorySlug), [categorySlug]);
  const [subcategories, setSubcategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!categorySlug) return;
    const loadSubcategories = async () => {
      try {
        setSubcategories(await getSubcategories(categorySlug));
      } catch (error) {
        console.error(error);
        toast.error(uiText("mbd2a0c457f519266"));
      } finally {
        setIsLoading(false);
      }
    };
    loadSubcategories();
  }, [categorySlug]);

  return (
    <div className="flex min-h-screen flex-col bg-white text-[#0F2654]">
      <NavBar />
      <main className="mx-auto w-full max-w-6xl flex-grow px-6 py-10">
        <Link
          href="/categories"
          className="text-sm font-semibold text-blue-700 hover:text-blue-900"
        >
          {uiText("md60f38c82f2cdf6f")}
        </Link>
        <div className="mb-8 mt-4">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
            {uiText("m292c06f0045a45d0")}
          </p>
          <h1 className="mt-2 text-3xl font-bold">{categoryLabel}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            {uiText("m58f5b0679f012219")}
          </p>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">
            {uiText("m4a02f25ecc26b9ca")}
          </p>
        ) : subcategories.length === 0 ? (
          <p className="text-sm text-slate-500">
            {uiText("m61647954e0c67a09")}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {subcategories.map((subcategory) => (
              <Link
                key={subcategory}
                href={`/categories/${encodeURIComponent(categorySlug)}/${slugify(subcategory)}`}
                className="rounded-2xl border border-blue-100 bg-blue-50 p-5 transition hover:border-blue-300 hover:bg-blue-100"
              >
                <h2 className="text-lg font-semibold">{subcategory}</h2>
                <p className="mt-2 text-sm text-slate-600">
                  {uiText("m310b1f3b3d1fccb3")}
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
