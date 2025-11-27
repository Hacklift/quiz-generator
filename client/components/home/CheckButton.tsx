"use client";

import React from "react";

interface CheckButtonProps {
  onClick: () => void;
}

export default function CheckButton({ onClick }: CheckButtonProps) {
  return (
    <button
      onClick={onClick}
      className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm"
    >
      Check Quiz
    </button>
  );
}
