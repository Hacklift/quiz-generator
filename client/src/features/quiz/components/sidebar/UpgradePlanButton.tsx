"use client";

import React, { useState } from "react";
import UpgradePlanModal from "@features/quiz/components/modals/UpgradePlanModal";
import SidebarButton from "./SidebarButton";

const UpgradePlanButton: React.FC = () => {
  const [isUpgradeOpen, setIsUpgradeOpen] = useState(false);

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
