"use client";

import React, { useState } from "react";
import { X, ChevronDown } from "lucide-react";

interface OrganizeModalProps<T> {
  title: string;
  items: T[];
  onClose: () => void;
  onOrganized: (sorted: T[]) => void;
  renderItem: (item: T, index: number) => React.ReactNode;
}

function OrganizeModal<
  T extends { title?: string; name?: string; created_at?: string },
>({ title, items, onClose, onOrganized, renderItem }: OrganizeModalProps<T>) {
  const [mode, setMode] = useState<"select" | "manual">("select");
  const [expanded, setExpanded] = useState<"date" | "alpha" | null>(null);
  const [sortedItems, setSortedItems] = useState<T[]>(items);

  const sortByDate = (order: "asc" | "desc") => {
    const sorted = [...items].sort((a, b) => {
      const dateA = new Date(a.created_at || "").getTime();
      const dateB = new Date(b.created_at || "").getTime();
      return order === "asc" ? dateA - dateB : dateB - dateA;
    });
    setSortedItems(sorted);
    onOrganized(sorted);
    onClose();
  };

  const sortByAlphabet = (order: "asc" | "desc") => {
    const sorted = [...items].sort((a, b) => {
      const nameA = (a.title || a.name || "").toLowerCase();
      const nameB = (b.title || b.name || "").toLowerCase();
      return order === "asc"
        ? nameA.localeCompare(nameB)
        : nameB.localeCompare(nameA);
    });
    setSortedItems(sorted);
    onOrganized(sorted);
    onClose();
  };

  const moveItem = (from: number, to: number) => {
    const updated = [...sortedItems];
    const [moved] = updated.splice(from, 1);
    updated.splice(to, 0, moved);
    setSortedItems(updated);
  };

  const handleSave = () => {
    onOrganized(sortedItems);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-navy-900">{title}</h2>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500 hover:text-gray-700" />
          </button>
        </div>

        {mode === "select" ? (
          <>
            <p className="text-gray-600 mb-4">
              Choose how you want to organize:
            </p>
            <div className="flex flex-col gap-3">
              <div>
                <button
                  onClick={() =>
                    setExpanded(expanded === "date" ? null : "date")
                  }
                  className="w-full flex justify-between items-center border rounded-lg py-2 px-3 hover:bg-gray-100 text-sm"
                >
                  <span>📅 By Date</span>
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${
                      expanded === "date" ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {expanded === "date" && (
                  <div className="mt-2 ml-6 flex flex-col gap-2">
                    <button
                      onClick={() => sortByDate("asc")}
                      className="text-left text-sm text-gray-700 hover:bg-gray-100 px-2 py-1 rounded"
                    >
                      Oldest → Newest
                    </button>
                    <button
                      onClick={() => sortByDate("desc")}
                      className="text-left text-sm text-gray-700 hover:bg-gray-100 px-2 py-1 rounded"
                    >
                      Newest → Oldest
                    </button>
                  </div>
                )}
              </div>

              <div>
                <button
                  onClick={() =>
                    setExpanded(expanded === "alpha" ? null : "alpha")
                  }
                  className="w-full flex justify-between items-center border rounded-lg py-2 px-3 hover:bg-gray-100 text-sm"
                >
                  <span>🔤 By Alphabet</span>
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${
                      expanded === "alpha" ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {expanded === "alpha" && (
                  <div className="mt-2 ml-6 flex flex-col gap-2">
                    <button
                      onClick={() => sortByAlphabet("asc")}
                      className="text-left text-sm text-gray-700 hover:bg-gray-100 px-2 py-1 rounded"
                    >
                      A → Z
                    </button>
                    <button
                      onClick={() => sortByAlphabet("desc")}
                      className="text-left text-sm text-gray-700 hover:bg-gray-100 px-2 py-1 rounded"
                    >
                      Z → A
                    </button>
                  </div>
                )}
              </div>

              <button
                onClick={() => setMode("manual")}
                className="w-full flex justify-between items-center border rounded-lg py-2 px-3 hover:bg-gray-100 text-sm"
              >
                ✋ Manual Reorder
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-2 mb-6">
              {sortedItems.map((item, index) => (
                <div
                  key={index}
                  className="flex justify-between items-center bg-gray-100 rounded-lg p-3"
                >
                  {renderItem(item, index)}

                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        moveItem(index, index - 1 >= 0 ? index - 1 : index)
                      }
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      ↑
                    </button>
                    <button
                      onClick={() =>
                        moveItem(
                          index,
                          index + 1 < sortedItems.length ? index + 1 : index,
                        )
                      }
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      ↓
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-2 rounded-xl shadow-md transition text-sm"
              >
                Save Order
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default OrganizeModal;
