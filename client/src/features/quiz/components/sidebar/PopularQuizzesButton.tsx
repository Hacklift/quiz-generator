"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import SidebarButton from "./SidebarButton";

const PopularQuizzesButton = ({ label }: { label: string }) => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname?.startsWith("/popular") ?? false;

  return (
    <SidebarButton
      label={label}
      icon="🌟"
      onClick={() => router.push("/popular")}
      isActive={isActive}
    />
  );
};

export default PopularQuizzesButton;
