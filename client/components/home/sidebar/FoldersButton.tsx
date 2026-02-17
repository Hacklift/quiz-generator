"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "../../../contexts/authContext";
import SignInModal from "../../auth/SignInModal";

const FoldersButton = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  const handleOpenFolders = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/folders");
  };

  const isActive = pathname === "/folders";

  return (
    <>
      <SidebarButton
        label="Folders"
        icon="📁"
        onClick={handleOpenFolders}
        isActive={isActive}
      />
      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={() => {}}
      />
    </>
  );
};

export default FoldersButton;
