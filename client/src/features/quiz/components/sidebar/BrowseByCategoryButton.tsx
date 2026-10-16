import { useTranslation } from "react-i18next";
import React from "react";
import SidebarButton from "./SidebarButton";

interface BrowseByCategoryButtonProps {
  onBrowseClick: () => void;
}

const BrowseByCategoryButton: React.FC<BrowseByCategoryButtonProps> = ({
  onBrowseClick,
}) => {
  const { t: uiText } = useTranslation("ui");

  return (
    <SidebarButton
      label={uiText("mc487162ccd5d4c00")}
      icon="📚"
      onClick={onBrowseClick}
    />
  );
};

export default BrowseByCategoryButton;
