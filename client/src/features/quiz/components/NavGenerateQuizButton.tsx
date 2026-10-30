"use client";

import React from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { BTN_BASE } from "@shared/ui/quizwerk";
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
      className={`${BTN_BASE} shrink-0 text-brand transition hover:bg-ink/[0.05] ${className}`}
    >
      Create {t("quiz")}
    </button>
  );
};

export default NavGenerateQuizButton;
