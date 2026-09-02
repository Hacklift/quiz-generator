"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";

const QuizHistoryButton: React.FC<{ label: string }> = ({ label }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const isActive = pathname?.startsWith("/quiz_history") ?? false;

  const handleClick = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/quiz_history");
  };

  return (
    <>
      <SidebarButton
        label={label}
        icon="🕘"
        onClick={handleClick}
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

export default QuizHistoryButton;
