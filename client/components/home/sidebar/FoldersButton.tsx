"use client";

import React from "react";
import { useRouter } from "next/navigation";
import SidebarButton from "./SidebarButton";

const FoldersButton = () => {
  const router = useRouter();

  const handleOpenFolders = () => {
    router.push("/folders"); // ✅ Navigate to your folders page
  };

  return (
    <SidebarButton label="Folders" icon="📁" onClick={handleOpenFolders} />
  );
};

export default FoldersButton;
