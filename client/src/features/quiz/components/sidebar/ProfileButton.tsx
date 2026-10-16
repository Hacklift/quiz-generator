"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";

const ProfileButton = () => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const isActive = pathname === "/profile";

  const handleClick = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/profile");
  };

  return (
    <>
      <SidebarButton
        label={uiText("m991bfa015514f9d5")}
        icon="👤"
        isActive={isActive}
        onClick={handleClick}
      />
      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={() => {}}
      />
    </>
  );
};

export default ProfileButton;
