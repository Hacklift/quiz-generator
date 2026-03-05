"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import SidebarButton from "./SidebarButton";

const PopularQuizzesButton = () => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname?.startsWith("/popular") ?? false;

  return (
    <SidebarButton
      label="Popular Quizzes"
      icon="🌟"
      onClick={() => router.push("/popular")}
      isActive={isActive}
    />
  );
};

export default PopularQuizzesButton;
