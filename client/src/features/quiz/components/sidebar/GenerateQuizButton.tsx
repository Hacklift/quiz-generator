"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const GenerateQuizButton: React.FC<{ label: string }> = ({ label }) => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname === "/generate";

  return (
    <SidebarButton
      label={label}
      icon="🧠"
      onClick={() => router.push("/generate")}
      isActive={isActive}
    />
  );
};

export default GenerateQuizButton;
