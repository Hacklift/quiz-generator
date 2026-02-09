"use client";
import { toast } from "react-hot-toast";

export const showComingSoonToast = () => {
  toast("This feature is coming soon!", {
    icon: "⏳",
    duration: 3000,
    style: {
      borderRadius: "10px",
      background: "#333",
      color: "#fff",
    },
  });
};
