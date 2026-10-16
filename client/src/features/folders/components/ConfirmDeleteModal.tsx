"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import { motion } from "framer-motion";

interface ConfirmDeleteModalProps {
  selectedItems: string[];
  type: string;
  onClose: () => void;
  onDeleted: (deletedIds: string[]) => void;
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  selectedItems,
  type,
  onClose,
  onDeleted,
}) => {
  const { t: uiText } = useTranslation("ui");

  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    try {
      setLoading(true);

      await new Promise((resolve) => setTimeout(resolve, 1000));

      onDeleted(selectedItems);
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
          {uiText("ma7f54311a3e625f5")}
        </h2>

        <p className="text-gray-700 mb-6">
          {uiText("m3a57bb9fb3bf7756")}{" "}
          <span className="font-semibold">{selectedItems.length}</span>{" "}
          {selectedItems.length === 1
            ? type
            : uiText("m852fe3718c6cfd72", { value0: type })}
          ?
        </p>

        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 bg-gray-300 rounded-md hover:bg-gray-400 disabled:opacity-60"
          >
            {uiText("m19766ed6ccb2f4a3")}
          </button>
          <button
            onClick={handleDelete}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-60"
          >
            {loading
              ? uiText("m685ecb984ac29ce8")
              : uiText("me2d0a54968ead24e")}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ConfirmDeleteModal;
