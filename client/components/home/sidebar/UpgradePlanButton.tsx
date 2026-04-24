"use client";

import React, { useState } from "react";
import SidebarButton from "./SidebarButton";
import UpgradePlanModal from "../modals/UpgradePlanModal";

const UpgradePlanButton: React.FC = () => {
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);

  const handleClick = () => {
    setIsUpgradeModalOpen(true);
  };

  return (
    <>
      <SidebarButton
        label="Upgrade Plan"
        icon="🚀"
        onClick={handleClick}
        isActive={isUpgradeModalOpen}
      />
      <UpgradePlanModal
        isOpen={isUpgradeModalOpen}
        onClose={() => setIsUpgradeModalOpen(false)}
      />
    </>
  );
};

export default UpgradePlanButton;
