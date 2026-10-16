import { useTranslation } from "react-i18next";
import React from "react";

interface SignUpButtonProps {
  onOpen: () => void;
  className?: string;
}

const SignUpButton: React.FC<SignUpButtonProps> = ({
  onOpen,
  className = "",
}) => {
  const { t: uiText } = useTranslation("ui");

  return (
    <button
      type="button"
      onClick={onOpen}
      className={`
        text-base font-semibold text-white 
        bg-[#0F2654] rounded-2xl px-6 py-2 
        hover:bg-[#0c2145] transition
        ${className}
      `}
    >
      {uiText("m47de23586e49d833")}
    </button>
  );
};

export default SignUpButton;
