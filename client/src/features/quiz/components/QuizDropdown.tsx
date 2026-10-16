import { useTranslation } from "react-i18next";
import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

const QuizDropdown: React.FC = () => {
  const { t: uiText } = useTranslation("ui");

  const [isOpen, setIsOpen] = useState<boolean>(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={uiText("m6eb376846967650a")}
        className="flex items-center text-base font-semibold text-black hover:opacity-80 transition"
      >
        {uiText("mde53383db46551cc")}
        <ChevronDown className="ml-1" size={20} />
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5"></div>
      )}
    </div>
  );
};

export default QuizDropdown;
