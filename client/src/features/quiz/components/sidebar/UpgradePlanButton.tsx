"use client";

import React, { useState } from "react";
import UpgradePlanModal from "@features/quiz/components/modals/UpgradePlanModal";
import SidebarButton from "./SidebarButton";
import { useAuth } from "@features/auth/context/authContext";
import { billingPlans } from "@shared/config/billingPlans";

const UpgradePlanButton: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [isUpgradeOpen, setIsUpgradeOpen] = useState(false);

  const activePlanConfig = billingPlans.find(
    (bp) => bp.action === user?.subscription_plan
  );

  const isPremium =
    isAuthenticated &&
    user?.subscription_status === "active" &&
    user?.subscription_plan !== "free" &&
    !!activePlanConfig;

  if (isPremium && activePlanConfig) {
    return (
      <div className="w-full flex items-center justify-between px-2 py-2 border border-[#C9C9C9] border-l-4 border-l-[#0F6BFF] rounded-md text-left font-medium text-sm shadow-sm bg-[#001F3F] text-white select-none">
        <div className="flex items-center gap-1">
          <span className="text-xl">👑</span>
          <span className="whitespace-nowrap font-semibold">
            {activePlanConfig.plan} Plan
          </span>
        </div>
        <span className="text-[10px] uppercase bg-[#0F6BFF] mx-1 px-1.5 py-0.5 rounded font-bold tracking-wider animate-pulse">
          Activated
        </span>
      </div>
    );
  }

  return (
    <>
      <SidebarButton
        label="Upgrade Plan"
        icon="🚀"
        onClick={() => setIsUpgradeOpen(true)}
      />
      <UpgradePlanModal
        isOpen={isUpgradeOpen}
        onClose={() => setIsUpgradeOpen(false)}
      />
    </>
  );
};

export default UpgradePlanButton;
