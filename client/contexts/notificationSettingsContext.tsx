import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useAuth } from "./authContext";

export interface NotificationDuration {
  short: number;
  medium: number;
  long: number;
}

export interface NotificationTypes {
  success: boolean;
  error: boolean;
  warning: boolean;
  info: boolean;
  quiz: boolean;
}

export interface NotificationSettings {
  user_id: string;
  enabled: boolean;
  theme: "dark" | "light";
  position: "top-right" | "top-left" | "bottom-right" | "bottom-left";
  sound: boolean;
  duration: NotificationDuration;
  types: NotificationTypes;
  created_at?: string;
  updated_at?: string;
}

interface NotificationSettingsContextType {
  settings: NotificationSettings | null;
  isLoading: boolean;
  updateSettings: (updates: Partial<NotificationSettings>) => Promise<void>;
  refreshSettings: () => Promise<void>;
}

const NotificationSettingsContext = createContext<
  NotificationSettingsContextType | undefined
>(undefined);

const defaultSettings: NotificationSettings = {
  user_id: "",
  enabled: true,
  theme: "dark",
  position: "top-right",
  sound: false,
  duration: {
    short: 2000,
    medium: 4000,
    long: 6000,
  },
  types: {
    success: true,
    error: true,
    warning: true,
    info: true,
    quiz: true,
  },
};

export const NotificationSettingsProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const { user, isAuthenticated } = useAuth();
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setSettings(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const response = await fetch("/api/v1/user/notification-settings", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      } else {
        setSettings(defaultSettings);
      }
    } catch (error) {
      console.error("Failed to fetch notification settings:", error);
      setSettings(defaultSettings);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user]);

  const updateSettings = useCallback(
    async (updates: Partial<NotificationSettings>) => {
      if (!isAuthenticated || !user) {
        throw new Error("Not authenticated");
      }

      try {
        const response = await fetch("/api/v1/user/notification-settings", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
          body: JSON.stringify(updates),
        });

        if (!response.ok) {
          throw new Error("Failed to update notification settings");
        }

        const updated = await response.json();
        setSettings(updated);
      } catch (error) {
        console.error("Failed to update notification settings:", error);
        throw error;
      }
    },
    [isAuthenticated, user]
  );

  const refreshSettings = useCallback(async () => {
    await fetchSettings();
  }, [fetchSettings]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchSettings();
    } else {
      setSettings(null);
      setIsLoading(false);
    }
  }, [isAuthenticated, fetchSettings]);

  return (
    <NotificationSettingsContext.Provider
      value={{
        settings: settings || defaultSettings,
        isLoading,
        updateSettings,
        refreshSettings,
      }}
    >
      {children}
    </NotificationSettingsContext.Provider>
  );
};

export const useNotificationSettings = () => {
  const context = useContext(NotificationSettingsContext);
  if (context === undefined) {
    throw new Error(
      "useNotificationSettings must be used within NotificationSettingsProvider"
    );
  }
  return context;
};
