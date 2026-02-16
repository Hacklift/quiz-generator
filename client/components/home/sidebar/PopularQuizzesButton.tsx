"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import SidebarButton from "./SidebarButton";

const PopularQuizzesButton = () => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname === "/popular";

  const handleClick = () => {
    router.push("/popular");
  };

  return (
    <SidebarButton
      label="Popular Quizzes"
      icon="🌟"
      onClick={handleClick}
      isActive={isActive}
    />
  );
};

export default PopularQuizzesButton;
