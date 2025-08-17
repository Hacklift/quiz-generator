import React from "react";
import SidebarButton from "./SidebarButton";

interface BrowseByCategoryButtonProps {
  onBrowseClick: () => void;
}

const BrowseByCategoryButton: React.FC<BrowseByCategoryButtonProps> = ({
  onBrowseClick,
}) => {
  return (
    <SidebarButton
      label="Browse by Category"
      icon="📚"
      onClick={onBrowseClick}
    />
  );
};

export default BrowseByCategoryButton;
