"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const QuizHistoryButton: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname.startsWith("/quiz_history");

  const handleClick = () => {
    const userId = "userId";
    const query = new URLSearchParams({ userId }).toString();
    router.push(`/quiz_history?${query}`);
  };

  return (
    <SidebarButton
      label="Quiz History"
      icon="🕘"
      onClick={handleClick}
      isActive={isActive}
    />
  );
};

export default QuizHistoryButton;
