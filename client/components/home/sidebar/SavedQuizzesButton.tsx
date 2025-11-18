"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const SavedQuizzesButton = () => {
  const pathname = usePathname();
  const isActive = pathname === "/saved_quiz";

  return (
    <Link href="/saved_quiz">
      <SidebarButton label="Saved Quizzes" icon="💾" isActive={isActive} />
    </Link>
  );
};

export default SavedQuizzesButton;
