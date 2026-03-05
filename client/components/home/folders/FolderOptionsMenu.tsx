"use client";

import React, { useState, useRef, useEffect } from "react";
import { MoreVertical } from "lucide-react";

interface FolderOptionsMenuProps {
  onCreate: () => void;
  onOrganize: () => void;
  onDelete: () => void;
}

const FolderOptionsMenu: React.FC<FolderOptionsMenuProps> = ({
  onCreate,
  onOrganize,
  onDelete,
}) => {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="p-2 rounded-full hover:bg-gray-100 transition"
      >
        <MoreVertical className="text-navy-900" size={20} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-white shadow-lg rounded-xl border border-gray-100 z-20">
          <button
            onClick={() => {
              onOrganize();
              setOpen(false);
            }}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-navy-900"
          >
            Organize Folders
          </button>
          <button
            onClick={() => {
              onCreate();
              setOpen(false);
            }}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-navy-900"
          >
            Create Folder
          </button>
          <button
            onClick={() => {
              onDelete();
              setOpen(false);
            }}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-red-600"
          >
            Delete Folder
          </button>
        </div>
      )}
    </div>
  );
};

export default FolderOptionsMenu;
