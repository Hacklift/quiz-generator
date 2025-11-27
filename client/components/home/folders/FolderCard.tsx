import React from "react";
import Link from "next/link";

interface FolderCardProps {
  folder: {
    _id: string;
    name: string;
    quizzes: any[];
    created_at: string;
  };
  isSelected: boolean;
  onSelect: () => void;
}

const FolderCard: React.FC<FolderCardProps> = ({
  folder,
  isSelected,
  onSelect,
}) => {
  const quizCount = folder.quizzes?.length || 0;
  const formattedDate = new Date(folder.created_at).toLocaleDateString();

  return (
    <div
      className={`relative p-5 border rounded-2xl shadow-md transition-all duration-200 hover:shadow-lg hover:scale-[1.02] ${
        isSelected ? "border-navy-600 bg-blue-50" : "border-gray-200 bg-white"
      }`}
    >
      <div className="absolute top-4 right-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="w-4 h-4 cursor-pointer accent-navy-600"
        />
      </div>

      <div className="mb-4">
        <h2 className="text-xl font-semibold text-navy-900 truncate">
          {folder.name}
        </h2>
        <p className="text-sm text-gray-500">
          {quizCount} quiz{quizCount !== 1 ? "zes" : ""}
        </p>
        <p className="text-xs text-gray-400 mt-1">Created: {formattedDate}</p>
      </div>

      <div className="mt-4">
        <Link href={`/folders/${folder._id}`} className="block">
          <button
            className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm"
            type="button"
          >
            Open Folder
          </button>
        </Link>
      </div>
    </div>
  );
};

export default FolderCard;
