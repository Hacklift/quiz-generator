"use client";

import React from "react";
import { usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { showComingSoonToast } from "../../ui/ComingSoonToast";

const PopularQuizzesButton = () => {
  const pathname = usePathname();
  const isActive = pathname === "/popular";

  return (
    <SidebarButton
      label="Popular Quizzes"
      icon="🌟"
      onClick={showComingSoonToast}
      isActive={isActive}
    />
  );
};

export default PopularQuizzesButton;
