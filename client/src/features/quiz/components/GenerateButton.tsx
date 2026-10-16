import { useTranslation } from "react-i18next";
import React from "react";
import { GenerateButtonProps } from "@shared/types/props";

const GenerateButton: React.FC<GenerateButtonProps> = ({
  onClick,
  loading,
}) => {
  const { t: uiText } = useTranslation("ui");
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full bg-[#0a3264] text-white font-semibold py-3 rounded-xl shadow-md hover:bg-[#082952] transition text-lg flex justify-center items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {loading ? (
        <>
          <svg
            className="animate-spin h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            ></path>
          </svg>
          <span>{uiText("m49286f33b674a0a6")}</span>
        </>
      ) : (
        uiText("m5da69270e5973c17")
      )}
    </button>
  );
};

export default GenerateButton;
