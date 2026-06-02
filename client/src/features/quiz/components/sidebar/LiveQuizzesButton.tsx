"use client";

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Radio } from "lucide-react";
import { useAuth } from "../../../contexts/authContext";
import SignInModal from "../../auth/SignInModal";
import SidebarButton from "./SidebarButton";

const LiveQuizzesButton: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const isActive = pathname?.startsWith("/my-live-quizzes") ?? false;

  const handleClick = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/my-live-quizzes");
  };

  return (
    <>
      <SidebarButton
        label="Live Quizzes"
        icon={<Radio size={20} />}
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

export default LiveQuizzesButton;
