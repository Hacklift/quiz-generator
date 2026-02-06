"use client";

import React from "react";

export interface Folder {
  _id: string;
  name: string;
  quizzes?: any[];
}

interface FolderCardProps {
  folder: Folder;
  isSelected: boolean;
  onSelect: () => void;
}

const FolderCard: React.FC<FolderCardProps> = ({
  folder,
  isSelected,
  onSelect,
}) => {
  return (
    <div
      onClick={onSelect}
      className={`p-4 border rounded-xl cursor-pointer transition ${
        isSelected
          ? "border-navy-600 bg-blue-50"
          : "border-gray-200 hover:bg-gray-50"
      }`}
    >
      <h3 className="font-semibold text-navy-800">{folder.name}</h3>
      <p className="text-sm text-gray-500">
        {folder.quizzes?.length || 0} quizzes
      </p>
    </div>
  );
};

export default FolderCard;
