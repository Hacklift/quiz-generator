"use client";

import React from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
interface NavGenerateQuizButtonProps {
  className?: string;
}

const NavGenerateQuizButton: React.FC<NavGenerateQuizButtonProps> = ({
  className = "",
}) => {
  const router = useRouter();
  const t = useTerms();

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
      Create {t("quiz")}
    </button>
  );
};

export default NavGenerateQuizButton;
