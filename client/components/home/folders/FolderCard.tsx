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
  onOpen: () => void;
  onToggleSelect: () => void;
}

const FolderCard: React.FC<FolderCardProps> = ({
  folder,
  isSelected,
  onOpen,
  onToggleSelect,
}) => {
  return (
    <div
      onClick={onOpen}
      className={`p-4 border rounded-xl cursor-pointer transition ${
        isSelected
          ? "border-navy-600 bg-blue-50"
          : "border-gray-200 hover:bg-gray-50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-navy-800">{folder.name}</h3>
          <p className="text-sm text-gray-500">
            {folder.quizzes?.length || 0} quizzes
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              onToggleSelect();
            }}
            onClick={(e) => e.stopPropagation()}
          />
          Select
        </label>
      </div>
    </div>
  );
};

export default FolderCard;
