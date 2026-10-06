import { api } from "@shared/api/http";

export type NotificationType = "payment" | "security" | "system" | "admin" | "training";

export interface NotificationItem {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: NotificationType;
  read: boolean;
  action_url?: string | null;
  created_at: string;
  expires_at?: string | null;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  unread_count: number;
  has_more: boolean;
}

export interface AdminNotificationPayload {
  user_id: string;
  title: string;
  message: string;
  type: NotificationType;
  action_url?: string;
  expires_at?: string;
}

export interface BroadcastNotificationPayload {
  title: string;
  message: string;
  type: NotificationType;
  action_url?: string;
  expires_at?: string;
  active_users_only: boolean;
}

export interface BroadcastNotificationResponse {
  message: string;
  created_count: number;
}

export const getNotifications = async ({
  limit = 20,
  skip = 0,
}: {
  limit?: number;
  skip?: number;
} = {}): Promise<NotificationListResponse> => {
  const response = await api.get("/api/notifications/", {
    params: { limit, skip },
  });
  return response.data;
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

export const createAdminNotification = async (
  payload: AdminNotificationPayload,
): Promise<NotificationItem> => {
  const response = await api.post("/api/notifications/", payload);
  return response.data;
};

export const broadcastNotification = async (
  payload: BroadcastNotificationPayload,
): Promise<BroadcastNotificationResponse> => {
  const response = await api.post("/api/notifications/broadcast", payload);
  return response.data;
};
