import React from "react";
import Link from "next/link";

interface SidebarButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  isActive?: boolean;
  href?: string;
}

export default function SidebarButton({
  icon,
  label,
  onClick,
  isActive,
  href,
}: SidebarButtonProps) {
  const className = `w-full flex items-center gap-3 px-4 py-2 border border-[#C9C9C9] border-l-4 rounded-md text-left font-medium text-sm shadow-sm transition-colors duration-200
        ${
          isActive
            ? "bg-[#001F3F] text-white border-[#001F3F] border-l-[#0F6BFF]"
            : "bg-[#E4E4E4] text-[#1A1A1A] border-l-transparent hover:bg-[#d3d3d3]"
        }`;
  const content = (
    <>
      <span className="shrink-0 text-xl">{icon}</span>
      <span className="min-w-0 break-words">{label}</span>
    </>
  );
  return href ? (
    <Link href={href} onClick={onClick} className={className}>{content}</Link>
  ) : (
    <button type="button" onClick={onClick} className={className}>{content}</button>
  );
}
