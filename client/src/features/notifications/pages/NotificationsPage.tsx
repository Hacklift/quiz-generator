"use client";
import { useTranslation } from "react-i18next";

import { useEffect, useMemo, useState } from "react";
import { CheckCheck, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationItem,
} from "@features/notifications/api/notificationsApi";

type Filter = "all" | "unread" | "read";

const PAGE_SIZE = 20;

const formatDate = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

export default function NotificationsPage() {
  const { t: uiText } = useTranslation("ui");

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");

  const loadNotifications = async (skip = 0) => {
    const data = await getNotifications({ limit: PAGE_SIZE, skip });
    setUnreadCount(data.unread_count);
    setHasMore(data.has_more);
    setNotifications((current) =>
      skip === 0 ? data.notifications : [...current, ...data.notifications],
    );
  };

  useEffect(() => {
    const loadInitial = async () => {
      try {
        setIsLoading(true);
        await loadNotifications(0);
      } catch (error) {
        console.error("Failed to load notifications:", error);
        toast.error(uiText("mc97d948c5ac9e1d7"));
      } finally {
        setIsLoading(false);
      }
    };

    loadInitial();
  }, []);

  const filteredNotifications = useMemo(() => {
    if (filter === "unread") {
      return notifications.filter((notification) => !notification.read);
    }
    if (filter === "read") {
      return notifications.filter((notification) => notification.read);
    }
    return notifications;
  }, [filter, notifications]);

  const handleMarkRead = async (notification: NotificationItem) => {
    if (notification.read) return;

    try {
      await markNotificationRead(notification.id);
      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id ? { ...item, read: true } : item,
        ),
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (error: any) {
      toast.error(error?.message || "Failed to update notification");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((current) =>
        current.map((notification) => ({ ...notification, read: true })),
      );
      setUnreadCount(0);
    } catch (error: any) {
      toast.error(error?.message || "Failed to update notifications");
    }
  };

  const handleDelete = async (notificationId: string) => {
    try {
      await deleteNotification(notificationId);
      setNotifications((current) =>
        current.filter((notification) => notification.id !== notificationId),
      );
      const data = await getNotifications({ limit: 1, skip: 0 });
      setUnreadCount(data.unread_count);
    } catch (error: any) {
      toast.error(error?.message || "Failed to delete notification");
    }
  };

  const handleLoadMore = async () => {
    try {
      setIsLoadingMore(true);
      await loadNotifications(notifications.length);
    } catch (error: any) {
      toast.error(error?.message || "Failed to load more notifications");
    } finally {
      setIsLoadingMore(false);
    }
  };

  return (
    <RequireAuth
      title={uiText("m788011833a5a0f22")}
      description={uiText("m7d3c99ec85060ddc")}
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />

        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-4xl">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-[#0F2654]">
                  {uiText("m788011833a5a0f22")}
                </h1>
                <p className="mt-1 text-sm text-gray-600">
                  {unreadCount} {uiText("m197674f294c4feca")}
                  {unreadCount === 1 ? "" : "s"}
                </p>
              </div>
              <button
                type="button"
                onClick={handleMarkAllRead}
                disabled={unreadCount === 0}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#0F2654] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#173773] disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                <CheckCheck size={18} />
                {uiText("m3bc62a9e6a39484a")}
              </button>
            </div>

            <div className="mb-5 flex rounded-lg border border-gray-200 bg-white p-1">
              {(["all", "unread", "read"] as Filter[]).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold capitalize transition ${
                    filter === item
                      ? "bg-[#0F2654] text-white"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>

            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
              {isLoading ? (
                <div className="flex min-h-64 items-center justify-center">
                  <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0F2654]" />
                </div>
              ) : filteredNotifications.length === 0 ? (
                <div className="px-6 py-16 text-center text-gray-600">
                  {uiText("me14023d3dd094f7f")}
                </div>
              ) : (
                filteredNotifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`border-b border-gray-100 px-5 py-4 last:border-b-0 ${
                      notification.read ? "bg-white" : "bg-blue-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <button
                          type="button"
                          onClick={() => handleMarkRead(notification)}
                          className="w-full text-left"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-base font-semibold text-gray-900">
                              {notification.title}
                            </h2>
                            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium capitalize text-gray-600">
                              {notification.type}
                            </span>
                            {!notification.read && (
                              <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
                                {uiText("m18fdd549b2ed367a")}
                              </span>
                            )}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-gray-700">
                            {notification.message}
                          </p>
                          <p className="mt-3 text-xs text-gray-400">
                            {formatDate(notification.created_at)}
                          </p>
                        </button>
                        {notification.action_url && (
                          <a
                            href={notification.action_url}
                            className="mt-3 inline-block text-sm font-semibold text-[#0F2654] underline"
                          >
                            {uiText("maab63f85c7f1cd14")}
                          </a>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDelete(notification.id)}
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-gray-500 transition hover:bg-red-50 hover:text-red-600"
                        aria-label={uiText("m511c885008e479ce")}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {hasMore && filter === "all" && (
              <div className="mt-6 flex justify-center">
                <button
                  type="button"
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  className="rounded-lg border border-[#0F2654] px-5 py-2 text-sm font-semibold text-[#0F2654] transition hover:bg-[#0F2654] hover:text-white disabled:cursor-not-allowed disabled:border-gray-400 disabled:text-gray-400"
                >
                  {isLoadingMore
                    ? uiText("m47d2a515ef2f05b8")
                    : uiText("mac8991ef01019cf5")}
                </button>
              </div>
            )}
          </div>
        </main>

        <Footer />
      </div>
    </RequireAuth>
  );
}
