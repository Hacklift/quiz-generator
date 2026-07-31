import React from "react";
import {
  getUserTypeDefinition,
  type PersonaUserType,
} from "@shared/config/persona";

/** "Set up for: Teacher" chip. */
export default function PersonaBadge({
  userType,
  className = "",
}: {
  userType: PersonaUserType;
  className?: string;
}) {
  return (
    <p
      className={`inline-flex items-center gap-2 bg-brand-100 px-3 py-1.5 text-sm font-semibold text-brand-700 ${className}`}
    >
      <span className="h-2 w-2 bg-brand" aria-hidden="true" />
      Set up for: {getUserTypeDefinition(userType).label}
    </p>
  );
}
