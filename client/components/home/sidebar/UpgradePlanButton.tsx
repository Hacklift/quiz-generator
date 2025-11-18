"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const UpgradePlanButton: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = pathname === "/#pricing";

  return (
    <SidebarButton
      label="Upgrade Plan"
      icon="🚀"
      onClick={() => router.push("/#pricing")}
      isActive={isActive}
    />
  );
};

export default UpgradePlanButton;
