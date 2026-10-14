import { useTranslation } from "react-i18next";
("use client"); // Mark this component as a client component

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function Quiz() {
  const { t: uiText } = useTranslation("ui");

  const [score, setScore] = useState<number | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const [parsedQuestions, setParsedQuestions] = useState<
    { question: string; answer: string }[]
  >([]);
  const [error, setError] = useState<string | null>(null); // Add an error state

  useEffect(() => {
    const query = searchParams?.get("questions");

    try {
      const questions = query ? JSON.parse(query) : []; // Safely parse the query
      if (Array.isArray(questions)) {
        setParsedQuestions(questions);
      } else {
        throw new Error("Invalid question format"); // If it's not an array, throw an error
      }
    } catch (err) {
      setError(uiText("m20d1e0c46eefa599"));
    }
  }, [searchParams]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setScore(10); // Placeholder for score calculation logic
  };

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <h1 className="text-3xl font-bold text-center mb-8">
          {uiText("m54a0e8c17ebb21a1")}
        </h1>
        <p className="text-center text-red-500">{error}</p>
        <button
          onClick={() => router.push("/")}
          className="bg-blue-500 text-white px-4 py-2 rounded mt-4"
        >
          {uiText("meec78426776352f1")}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8">
      <h1 className="text-3xl font-bold text-center mb-8">
        {uiText("mc136c5010420662a")}
      </h1>
      {score === null ? (
        <form onSubmit={handleSubmit}>
          {parsedQuestions.map((q, index) => (
            <div key={index} className="mb-6">
              <p className="text-xl mb-2">{q.question}</p>
              <input
                type="text"
                className="w-full p-2 border border-gray-300 rounded"
              />
            </div>
          ))}
          <button
            type="submit"
            className="bg-green-500 text-white px-4 py-2 rounded"
          >
            {uiText("m1ff0f3bdfbd0fe14")}
          </button>
        </form>
      ) : (
        <div className="text-center">
          <h2 className="text-2xl mb-4">
            {uiText("m02bad385814e4a5f")}
            {score} / {parsedQuestions.length}
          </h2>
          <button
            onClick={() => router.push("/")}
            className="bg-blue-500 text-white px-4 py-2 rounded"
          >
            {uiText("meec78426776352f1")}
          </button>
        </div>
      )}
    </div>
  );
}
