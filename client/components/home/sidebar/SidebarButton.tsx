import React from "react";

interface SidebarButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  isActive?: boolean;
}

export default function SidebarButton({
  icon,
  label,
  onClick,
  isActive,
}: SidebarButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-2 border border-[#C9C9C9] border-l-4 rounded-md text-left font-medium text-sm shadow-sm transition-colors duration-200
        ${
          isActive
            ? "bg-[#001F3F] text-white border-[#001F3F] border-l-[#0F6BFF]"
            : "bg-[#E4E4E4] text-[#1A1A1A] border-l-transparent hover:bg-[#d3d3d3]"
        }`}
    >
      <span className="text-xl">{icon}</span>
      <span className="whitespace-nowrap">{label}</span>
    </button>
  );
}
