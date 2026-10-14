"use client";
import { useTranslation } from "react-i18next";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, CheckCheck, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { ROUTES } from "@shared/config/patterns/routes";
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationItem,
} from "@features/notifications/api/notificationsApi";

const formatNotificationDate = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

const NotificationBell = () => {
  const { t: uiText } = useTranslation("ui");

  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const loadNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getNotifications({ limit: 8, skip: 0 });
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    const intervalId = window.setInterval(loadNotifications, 60000);
    return () => window.clearInterval(intervalId);
  }, [loadNotifications]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleOpen = () => {
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);
    if (nextOpen) {
      loadNotifications();
    }
  };

  const handleMarkRead = async (notification: NotificationItem) => {
    if (!notification.read) {
      await markNotificationRead(notification.id);
      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id ? { ...item, read: true } : item,
        ),
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    }
  };

  const handleDelete = async (
    event: React.MouseEvent<HTMLButtonElement>,
    notificationId: string,
  ) => {
    event.stopPropagation();
    try {
      await deleteNotification(notificationId);
      setNotifications((current) =>
        current.filter((item) => item.id !== notificationId),
      );
      await loadNotifications();
    } catch (error: any) {
      toast.error(error?.message || "Failed to delete notification");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((current) =>
        current.map((item) => ({ ...item, read: true })),
      );
      setUnreadCount(0);
    } catch (error: any) {
      toast.error(error?.message || "Failed to update notifications");
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={handleOpen}
        className="relative flex h-10 w-10 items-center justify-center rounded-full text-[#0F2654] transition hover:bg-white/70 focus:outline-none focus:ring-2 focus:ring-[#0F2654]"
        aria-label={uiText("m4e2fa50f7e951e42")}
      >
        <Bell size={22} />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-xs font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-1/2 z-50 mt-3 w-[min(22rem,calc(100vw-2rem))] translate-x-1/2 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl md:right-0 md:translate-x-0">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-[#0F2654]">
              {uiText("m788011833a5a0f22")}
            </h2>
            <button
              type="button"
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              className="flex items-center gap-1 text-xs font-medium text-[#0F2654] disabled:cursor-not-allowed disabled:text-gray-400"
            >
              <CheckCheck size={15} />
              {uiText("m3bc62a9e6a39484a")}
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {isLoading && notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                {uiText("mf3484ee688e711b7")}
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                {uiText("mca02c722b0986174")}
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`group border-b border-gray-100 px-4 py-3 last:border-b-0 ${
                    notification.read ? "bg-white" : "bg-blue-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => handleMarkRead(notification)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="truncate text-sm font-semibold text-gray-900">
                        {notification.title}
                      </p>
                      <p className="mt-1 line-clamp-2 text-sm text-gray-600">
                        {notification.message}
                      </p>
                      <p className="mt-2 text-xs text-gray-400">
                        {formatNotificationDate(notification.created_at)}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={(event) => handleDelete(event, notification.id)}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-gray-400 transition hover:bg-red-50 hover:text-red-600"
                      aria-label={uiText("m511c885008e479ce")}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <Link
            href={ROUTES.NOTIFICATIONS}
            onClick={() => setIsOpen(false)}
            className="block border-t border-gray-200 px-4 py-3 text-center text-sm font-semibold text-[#0F2654] hover:bg-gray-50"
          >
            {uiText("m13af64d6684970df")}
          </Link>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
