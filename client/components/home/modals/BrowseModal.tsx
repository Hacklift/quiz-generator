"use client";

import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Dialog } from "@headlessui/react";
import { X } from "lucide-react";

interface Quiz {
  question: string;
  options?: string[];
  answer: string;
  subcategory?: string;
  question_type?: string;
}

interface BrowseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const BrowseModal: React.FC<BrowseModalProps> = ({ isOpen, onClose }) => {
  const [categories, setCategories] = useState<string[]>([]);
  const [subcategories, setSubcategories] = useState<string[]>([]);
  const [quizTypes, setQuizTypes] = useState<string[]>([]);
  const [filteredTypes, setFilteredTypes] = useState<string[]>([]);
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [search, setSearch] = useState<string>("");

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<string | null>(
    null,
  );
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [currentIndex, setCurrentIndex] = useState<number>(0);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

  const resetState = () => {
    setCategories([]);
    setSubcategories([]);
    setQuizTypes([]);
    setFilteredTypes([]);
    setQuizzes([]);
    setSearch("");
    setSelectedCategory(null);
    setSelectedSubcategory(null);
    setSelectedType(null);
    setPage(1);
    setCurrentIndex(0);
    setHasMore(true);
  };

  const fetchCategories = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/api/categories`);
      setCategories(data);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  }, [API_BASE]);

  useEffect(() => {
    if (isOpen) {
      resetState();
      fetchCategories();
    }
  }, [fetchCategories, isOpen]);

  const fetchSubcategories = async (category: string) => {
    try {
      const { data } = await axios.get(
        `${API_BASE}/api/category/${category}/subcategories`,
      );
      setSubcategories(data);
    } catch (err) {
      console.error("Error fetching subcategories:", err);
    }
  };

  const fetchQuizTypes = async (category: string, subcategory: string) => {
    try {
      const { data } = await axios.get(
        `${API_BASE}/api/category/${category}/subcategory/${subcategory}/types`,
      );
      setQuizTypes(data);
      setFilteredTypes(data);
      setSelectedType(null);
      setQuizzes([]);
      setPage(1);
      setCurrentIndex(0);
      setHasMore(true);
    } catch (err) {
      console.error("Error fetching quiz types:", err);
    }
  };

  const fetchQuizzes = async (
    category: string,
    subcategory: string,
    type: string,
    pageNum: number = 1,
  ) => {
    try {
      const { data } = await axios.get(
        `${API_BASE}/api/category/${category}/subcategory/${subcategory}/type/${type}?page=${pageNum}&page_size=10`,
      );
      setHasMore(data.length === 10);
      setQuizzes(data);
      setCurrentIndex(0);
    } catch (err) {
      console.error("Error fetching quizzes:", err);
    }
  };

  const handleTypeSelect = (type: string) => {
    if (!selectedCategory || !selectedSubcategory) return;
    setSelectedType(type);
    setPage(1);
    setHasMore(true);
    fetchQuizzes(selectedCategory, selectedSubcategory, type, 1);
  };

  const handleNavigation = (direction: "next" | "prev") => {
    if (direction === "next") {
      if (currentIndex < quizzes.length - 1) {
        setCurrentIndex(currentIndex + 1);
      } else if (hasMore) {
        const nextPage = page + 1;
        setPage(nextPage);
        fetchQuizzes(
          selectedCategory!,
          selectedSubcategory!,
          selectedType!,
          nextPage,
        );
      }
    } else {
      if (currentIndex > 0) {
        setCurrentIndex(currentIndex - 1);
      }
    }
  };

  useEffect(() => {
    if (search) {
      const filtered = quizTypes.filter((type) =>
        type.toLowerCase().includes(search.toLowerCase()),
      );
      setFilteredTypes(filtered);
    } else {
      setFilteredTypes(quizTypes);
    }
  }, [search, quizTypes]);

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm"
        aria-hidden="true"
      />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-xl p-6 space-y-6">
          <div className="flex justify-between items-center border-b pb-2">
            <Dialog.Title className="text-xl font-bold text-[#0F2654]">
              Browse by Category
            </Dialog.Title>
            <button onClick={onClose}>
              <X className="w-6 h-6 text-gray-500 hover:text-gray-700" />
            </button>
          </div>

          {!selectedCategory ? (
            <>
              <p className="text-sm font-medium text-gray-700">
                Select a category
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => {
                      setSelectedCategory(cat);
                      fetchSubcategories(cat);
                    }}
                    className="bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-xl text-sm font-medium text-gray-800"
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </>
          ) : !selectedSubcategory ? (
            <>
              <p className="text-sm font-medium text-gray-700">
                Select a subcategory
              </p>
              <button
                onClick={() => setSelectedCategory(null)}
                className="text-sm text-blue-600 hover:underline"
              >
                ← Back to Categories
              </button>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-2">
                {subcategories.map((sub) => (
                  <button
                    key={sub}
                    onClick={() => {
                      setSelectedSubcategory(sub);
                      fetchQuizTypes(selectedCategory, sub);
                    }}
                    className="bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-xl text-sm font-medium text-gray-800"
                  >
                    {sub}
                  </button>
                ))}
              </div>
            </>
          ) : !selectedType ? (
            <>
              <p className="text-sm font-medium text-gray-700">
                Select a question type
              </p>
              <div className="flex items-center justify-between mt-2">
                <button
                  onClick={() => {
                    setSelectedSubcategory(null);
                    setQuizTypes([]);
                    setSearch("");
                    setFilteredTypes([]);
                  }}
                  className="text-sm text-blue-600 hover:underline"
                >
                  ← Back to Subcategories
                </button>
                <input
                  type="text"
                  placeholder="Filter quiz types..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="border px-3 py-2 rounded-md text-sm"
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-2">
                {filteredTypes.map((type) => (
                  <button
                    key={type}
                    onClick={() => handleTypeSelect(type)}
                    className="px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-200 bg-gray-100 hover:bg-gray-200"
                  >
                    {type}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  setSelectedType(null);
                  setQuizzes([]);
                  setPage(1);
                  setCurrentIndex(0);
                }}
                className="text-sm text-blue-600 hover:underline"
              >
                ← Back
              </button>
              {quizzes.length > 0 ? (
                <div className="mt-6 space-y-4">
                  <div className="bg-white p-4 border rounded-lg shadow-sm">
                    <h3 className="font-semibold text-gray-800">
                      {quizzes[currentIndex]?.question}
                    </h3>
                    {quizzes[currentIndex]?.options && (
                      <ul className="list-disc ml-5 mt-2 text-sm text-gray-700">
                        {quizzes[currentIndex].options.map((opt, i) => (
                          <li key={i}>{opt}</li>
                        ))}
                      </ul>
                    )}
                    <p className="mt-2 text-sm">
                      <strong>Answer:</strong> {quizzes[currentIndex].answer}
                    </p>
                    {quizzes[currentIndex].subcategory && (
                      <p className="text-xs text-gray-500 mt-1">
                        Subcategory: {quizzes[currentIndex].subcategory}
                      </p>
                    )}
                  </div>
                  <div className="flex justify-between mt-4">
                    <button
                      onClick={() => handleNavigation("prev")}
                      disabled={page === 1 && currentIndex === 0}
                      className="text-sm px-4 py-2 rounded-lg border bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
                    >
                      ← Previous
                    </button>
                    <button
                      onClick={() => handleNavigation("next")}
                      disabled={!hasMore && currentIndex >= quizzes.length - 1}
                      className="text-sm px-4 py-2 rounded-lg border bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      Next →
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-600 mt-4">
                  No quizzes available.
                </p>
              )}
            </>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default BrowseModal;
