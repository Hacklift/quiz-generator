import { api } from "./auth";

export type NotificationType = "payment" | "security" | "system" | "admin";
export type NotificationPriority = "high" | "medium" | "low";

export interface AppNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: NotificationType;
  priority: NotificationPriority;
  read: boolean;
  action_url?: string | null;
  created_at: string;
  read_at?: string | null;
  expires_at?: string | null;
}

export interface NotificationListResponse {
  notifications: AppNotification[];
  unread_count: number;
  has_more: boolean;
}

export interface BroadcastNotificationPayload {
  title: string;
  message: string;
  type?: NotificationType;
  priority?: NotificationPriority;
  action_url?: string | null;
  expires_at?: string | null;
  active_users_only?: boolean;
}

export interface BroadcastNotificationResponse {
  message: string;
  created_count: number;
}

export const getNotifications = async (
  limit = 20,
  skip = 0,
): Promise<NotificationListResponse> => {
  const response = await api.get("/api/notifications/", {
    params: { limit, skip },
  });
  return response.data as NotificationListResponse;
};

export const markNotificationRead = async (notificationId: string) => {
  const response = await api.patch(`/api/notifications/${notificationId}/read`);
  return response.data;
};

export const markAllNotificationsRead = async () => {
  const response = await api.patch("/api/notifications/read-all");
  return response.data;
};

export const deleteNotification = async (notificationId: string) => {
  const response = await api.delete(`/api/notifications/${notificationId}`);
  return response.data;
};

export const createBroadcastNotification = async (
  payload: BroadcastNotificationPayload,
): Promise<BroadcastNotificationResponse> => {
  const response = await api.post("/api/notifications/broadcast", payload);
  return response.data as BroadcastNotificationResponse;
};
