"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function NewQuizButton() {
  const router = useRouter();

  const handleClick = () => {
    router.push("/generate");
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-3 rounded-xl shadow-md transition text-base"
    >
      New Quiz
    </button>
  );
}
