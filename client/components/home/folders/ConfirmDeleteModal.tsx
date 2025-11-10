"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";

interface ConfirmDeleteModalProps {
  selectedItems: string[];
  type: string; // e.g. "folder" or "quiz"
  onClose: () => void;
  onDeleted: (deletedIds: string[]) => void;
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  selectedItems,
  type,
  onClose,
  onDeleted,
}) => {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    try {
      setLoading(true);

      // Simulate delete API call delay for now
      await new Promise((resolve) => setTimeout(resolve, 1000));

      onDeleted(selectedItems); // Pass back deleted IDs
      onClose();
    } catch (error) {
      console.error("Delete failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        <h2 className="text-2xl font-semibold text-navy-900 mb-4">
          Confirm Delete
        </h2>

        <p className="text-gray-700 mb-6">
          Are you sure you want to delete{" "}
          <span className="font-semibold">{selectedItems.length}</span>{" "}
          {selectedItems.length === 1 ? type : `${type}s`}?
        </p>

        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 bg-gray-300 rounded-md hover:bg-gray-400 disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-60"
          >
            {loading ? "Deleting..." : "Delete"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ConfirmDeleteModal;
