"use client";

import React from "react";
import { useRouter } from "next/router";
interface NavGenerateQuizButtonProps {
  className?: string;
}

const NavGenerateQuizButton: React.FC<NavGenerateQuizButtonProps> = ({
  className = "",
}) => {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push("/generate")}
      className={`
        text-base font-semibold text-[#0F2654] 
        border border-[#0F2654] rounded-2xl px-6 py-2 
        hover:bg-gray-100 transition
        ${className}
      `}
    >
      Generate a Quiz
    </button>
  );
};

export default NavGenerateQuizButton;
