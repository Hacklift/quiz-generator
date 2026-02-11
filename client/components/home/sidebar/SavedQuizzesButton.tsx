"use client";

import React from "react";
import Link from "next/link";
import SidebarButton from "./SidebarButton";

const SavedQuizzesButton = () => {
  return (
    <Link href="/saved_quiz">
      <SidebarButton label="Saved Quizzes" icon="💾" onClick={() => {}} />
    </Link>
  );
};

export default SavedQuizzesButton;
