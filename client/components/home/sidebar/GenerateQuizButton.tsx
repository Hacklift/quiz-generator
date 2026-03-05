"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const GenerateQuizButton: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname === "/generate";

  return (
    <SidebarButton
      label="Generate Quiz"
      icon="🧠"
      onClick={() => router.push("/generate")}
      isActive={isActive}
    />
  );
};

export default GenerateQuizButton;
