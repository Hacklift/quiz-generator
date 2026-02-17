"use client";

import React, { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";
import { useAuth } from "../../../contexts/authContext";
import SignInModal from "../../auth/SignInModal";

const UpgradePlanButton: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const isActive = pathname === "/#pricing";

  const handleClick = () => {
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    router.push("/#pricing");
  };

  return (
    <>
      <SidebarButton
        label="Upgrade Plan"
        icon="🚀"
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

export default UpgradePlanButton;
