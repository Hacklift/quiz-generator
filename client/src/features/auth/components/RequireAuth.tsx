"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "./SignInModal";

interface RequireAuthProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

const RequireAuth: React.FC<RequireAuthProps> = ({
  children,
  title,
  description,
}) => {
  const { t: uiText } = useTranslation("ui");
  const { t: authText } = useTranslation();

  const { isAuthenticated, isLoading } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center text-gray-700 px-4">
          <h1 className="text-2xl font-bold mb-2 text-[#0F2654]">
            {title ?? authText("auth.requiredTitle")}
          </h1>
          <p className="max-w-xl">
            {description ?? authText("auth.requiredDescription")}{" "}
            <button
              type="button"
              onClick={() => setIsLoginOpen(true)}
              className="text-blue-600 underline"
            >
              {uiText("mbfd402b2f6f38125")}
            </button>
            .
          </p>
        </div>

        <SignInModal
          isOpen={isLoginOpen}
          onClose={() => setIsLoginOpen(false)}
          switchToSignUp={() => {}}
        />
      </>
    );
  }

  return <>{children}</>;
};

export default RequireAuth;
