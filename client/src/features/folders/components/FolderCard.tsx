"use client";
import { useTranslation } from "react-i18next";

import React from "react";

export interface Folder {
  id?: string;
  _id?: string;
  name: string;
  quizzes?: any[];
  quiz_count?: number;
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
  const { t: uiText } = useTranslation("ui");

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
            {uiText("m55b18220390f39e3", {
              value0: folder.quizzes?.length ?? folder.quiz_count ?? 0,
            })}
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
          {uiText("m2a78025de6aae5e7")}
        </label>
      </div>
    </div>
  );
};

export default FolderCard;
