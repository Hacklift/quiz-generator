"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const FoldersButton = () => {
  const router = useRouter();
  const pathname = usePathname();

  const handleOpenFolders = () => {
    router.push("/folders");
  };

  const isActive = pathname === "/folders";

  return (
    <SidebarButton
      label="Folders"
      icon="📁"
      onClick={handleOpenFolders}
      isActive={isActive}
    />
  );
};

export default FoldersButton;
