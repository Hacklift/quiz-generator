import { toast, ToastOptions } from "react-hot-toast";
import { useNotificationSettings } from "../../contexts/notificationSettingsContext";

/* ---------------------------------- */
/* 🎯 Base Configuration              */
/* ---------------------------------- */

const durations = {
  short: 2000,
  medium: 4000,
  long: 6000,
};

const baseStyle: React.CSSProperties = {
  borderRadius: "10px",
  background: "#1e293b", // dark slate
  color: "#fff",
  padding: "12px 16px",
  fontSize: "14px",
};

/* Prevent stacking (single toast control) */
const TOAST_ID = "quiz-feedback";

/* Helper to merge options */
const withDefaults = (options?: ToastOptions): ToastOptions => ({
  position: "top-right",
  style: baseStyle,
  ...options,
});

/* ---------------------------------- */
/* 🚀 Notification System             */
/* ---------------------------------- */

export const notify = {
  /* ✅ Correct Answer */
  correct: (msg = "Correct answer! 🎉", options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.success(msg, {
      id: TOAST_ID,
      duration: durations.short,
      icon: "✅",
      ...withDefaults(options),
    });
  },

  /* ❌ Wrong Answer */
  wrong: (msg = "Wrong answer 😢", options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.error(msg, {
      id: TOAST_ID,
      duration: durations.medium,
      icon: "❌",
      ...withDefaults(options),
    });
  },

  /* ⏰ Time Up */
  timeUp: (msg = "Time's up! ⏰", options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast(msg, {
      id: TOAST_ID,
      duration: durations.medium,
      icon: "⏳",
      ...withDefaults(options),
    });
  },

  /* 🔥 Streak Feedback */
  streak: (count: number, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.success(`🔥 ${count} correct answers in a row!`, {
      id: TOAST_ID,
      duration: durations.short,
      ...withDefaults(options),
    });
  },

  /* 🚀 Level Up */
  levelUp: (level: number, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.success(`🚀 You reached Level ${level}!`, {
      id: TOAST_ID,
      duration: durations.long,
      ...withDefaults(options),
    });
  },

  /* ℹ️ Info */
  info: (msg: string, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast(msg, {
      id: TOAST_ID,
      duration: durations.medium,
      icon: "ℹ️",
      ...withDefaults(options),
    });
  },

  /* ❗ Error */
  error: (msg: string, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.error(msg, {
      id: TOAST_ID,
      duration: durations.long,
      ...withDefaults(options),
    });
  },

  /* 🎉 General Success */
  success: (msg: string, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast.success(msg, {
      id: TOAST_ID,
      duration: durations.short,
      ...withDefaults(options),
    });
  },

  /* 🧩 Custom */
  custom: (msg: string, options?: ToastOptions) => {
    toast.dismiss(TOAST_ID);
    toast(msg, {
      id: TOAST_ID,
      duration: durations.medium,
      ...withDefaults(options),
    });
  },
};

/* ---------------------------------- */
/* 🎯 Settings-Aware Notification Hook */
/* ---------------------------------- */

/**
 * Hook that provides notify functions respecting user settings
 * Checks if notifications are enabled and filters by type
 * Dynamically applies user's duration preferences
 */
export const useNotifyWithSettings = () => {
  const { settings } = useNotificationSettings();

  // Helper to apply user's duration preferences
  const getUserDuration = (defaultType: "short" | "medium" | "long"): number => {
    if (!settings || !settings.duration) return durations[defaultType];
    return settings.duration[defaultType];
  };

  // Helper to check if notification should show based on type
  const shouldShowNotification = (type: string): boolean => {
    if (!settings) return true; // Show if settings not loaded yet
    if (!settings.enabled) return false; // Master toggle off
    return (settings.types as any)[type] !== false; // Check specific type
  };

  // Helper to create options with user's position and duration
  const getOptions = (
    defaultDurationType: "short" | "medium" | "long",
    options?: ToastOptions
  ): ToastOptions => {
    if (!settings) {
      return withDefaults(options);
    }
    return {
      position: settings.position as any,
      duration: getUserDuration(defaultDurationType),
      style: {
        ...baseStyle,
        background: settings.theme === "light" ? "#f1f5f9" : baseStyle.background,
        color: settings.theme === "light" ? "#1e293b" : baseStyle.color,
      },
      ...options,
    };
  };

  return {
    correct: (msg = "Correct answer! 🎉", options?: ToastOptions) => {
      if (!shouldShowNotification("quiz")) return;
      toast.dismiss(TOAST_ID);
      toast.success(msg, {
        id: TOAST_ID,
        icon: "✅",
        ...getOptions("short", options),
      });
    },

    wrong: (msg = "Wrong answer 😢", options?: ToastOptions) => {
      if (!shouldShowNotification("quiz")) return;
      toast.dismiss(TOAST_ID);
      toast.error(msg, {
        id: TOAST_ID,
        icon: "❌",
        ...getOptions("medium", options),
      });
    },

    timeUp: (msg = "Time's up! ⏰", options?: ToastOptions) => {
      if (!shouldShowNotification("info")) return;
      toast.dismiss(TOAST_ID);
      toast(msg, {
        id: TOAST_ID,
        icon: "⏳",
        ...getOptions("medium", options),
      });
    },

    streak: (count: number, options?: ToastOptions) => {
      if (!shouldShowNotification("quiz")) return;
      toast.dismiss(TOAST_ID);
      toast.success(`🔥 ${count} correct answers in a row!`, {
        id: TOAST_ID,
        ...getOptions("short", options),
      });
    },

    levelUp: (level: number, options?: ToastOptions) => {
      if (!shouldShowNotification("success")) return;
      toast.dismiss(TOAST_ID);
      toast.success(`🚀 You reached Level ${level}!`, {
        id: TOAST_ID,
        ...getOptions("long", options),
      });
    },

    info: (msg: string, options?: ToastOptions) => {
      if (!shouldShowNotification("info")) return;
      toast.dismiss(TOAST_ID);
      toast(msg, {
        id: TOAST_ID,
        icon: "ℹ️",
        ...getOptions("medium", options),
      });
    },

    error: (msg: string, options?: ToastOptions) => {
      if (!shouldShowNotification("error")) return;
      toast.dismiss(TOAST_ID);
      toast.error(msg, {
        id: TOAST_ID,
        ...getOptions("long", options),
      });
    },

    success: (msg: string, options?: ToastOptions) => {
      if (!shouldShowNotification("success")) return;
      toast.dismiss(TOAST_ID);
      toast.success(msg, {
        id: TOAST_ID,
        ...getOptions("short", options),
      });
    },

    custom: (msg: string, options?: ToastOptions) => {
      if (!settings || !settings.enabled) return;
      toast.dismiss(TOAST_ID);
      toast(msg, {
        id: TOAST_ID,
        ...getOptions("medium", options),
      });
    },

    warning: (msg: string, options?: ToastOptions) => {
      if (!shouldShowNotification("warning")) return;
      toast.dismiss(TOAST_ID);
      toast(msg, {
        id: TOAST_ID,
        icon: "⚠️",
        ...getOptions("medium", options),
      });
    },
  };
};