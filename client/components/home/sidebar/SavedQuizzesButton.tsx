"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "../../../contexts/authContext";
import SignInModal from "../../auth/SignInModal";

const SavedQuizzesButton = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const isActive = pathname === "/saved_quiz";

  const handleClick = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/saved_quiz");
  };

  return (
    <>
      <SidebarButton
        label="Saved Quizzes"
        icon="💾"
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

export default SavedQuizzesButton;
