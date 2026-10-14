import { useTranslation } from "react-i18next";
import React from "react";

interface SignInButtonProps {
  onOpen: () => void;
  className?: string;
}

const SignInButton: React.FC<SignInButtonProps> = ({
  onOpen,
  className = "",
}) => {
  const { t: uiText } = useTranslation("ui");

  return (
    <button
      type="button"
      onClick={onOpen}
      className={`
        text-base font-semibold text-[#0F2654] 
        border border-[#0F2654] bg-white 
        rounded-2xl px-6 py-2 hover:bg-gray-100 transition
        ${className}
      `}
    >
      {uiText("mbcc0bcc9140b0c97")}
    </button>
  );
};

export default SignInButton;
