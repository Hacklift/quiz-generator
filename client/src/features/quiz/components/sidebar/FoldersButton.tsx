"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";

const FoldersButton = () => {
  const { t: uiText } = useTranslation("ui");

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
        label={uiText("mc4d6bb200f4c058a")}
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
