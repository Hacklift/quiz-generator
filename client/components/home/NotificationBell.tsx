"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import {
  Bell,
  CheckCheck,
  Trash2,
  X,
} from "lucide-react";
import {
  AppNotification,
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../../lib";
import { ROUTES } from "../../constants/patterns/routes";

const PAGE_SIZE = 20;

const formatRelativeTime = (value: string) => {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "";

  const seconds = Math.max(1, Math.floor((Date.now() - timestamp) / 1000));

  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min${minutes === 1 ? "" : "s"} ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(new Date(value));
};

const priorityStyles = {
  high: "border-l-red-500",
  medium: "border-l-[#0F2654]",
  low: "border-l-gray-300",
};

interface NotificationBellProps {
  label?: string;
  panelAlign?: "right" | "center";
}

const NotificationBell: React.FC<NotificationBellProps> = ({
  label,
  panelAlign = "right",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  const fetchNotifications = useCallback(async (skip = 0) => {
    const isFirstPage = skip === 0;
    if (isFirstPage) {
      setIsLoading(true);
    } else {
      setIsLoadingMore(true);
    }

    try {
      const data = await getNotifications(PAGE_SIZE, skip);
      setUnreadCount(data.unread_count);
      setHasMore(data.has_more);
      setNotifications((current) =>
        isFirstPage
          ? data.notifications
          : [...current, ...data.notifications],
      );
    } catch (error) {
      console.error("Failed to load notifications:", error);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = window.setInterval(() => fetchNotifications(), 60000);
    return () => window.clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [fetchNotifications, isOpen]);

  const handleRead = async (notification: AppNotification) => {
    if (!notification.read) {
      await markNotificationRead(notification.id);
      setNotifications((current) =>
        current.map((item) =>
          item.id === notification.id
            ? { ...item, read: true, read_at: new Date().toISOString() }
            : item,
        ),
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    }
  };

  const handleNotificationClick = async (notification: AppNotification) => {
    await handleRead(notification);
    setIsOpen(false);
    router.push(ROUTES.NOTIFICATIONS);
  };

  const handleDelete = async (
    event: React.MouseEvent<HTMLButtonElement>,
    notification: AppNotification,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    await deleteNotification(notification.id);
    setNotifications((current) =>
      current.filter((item) => item.id !== notification.id),
    );
    if (!notification.read) {
      setUnreadCount((count) => Math.max(0, count - 1));
    }
    fetchNotifications();
  };

  const handleReadAll = async () => {
    await markAllNotificationsRead();
    setNotifications((current) =>
      current.map((item) => ({
        ...item,
        read: true,
        read_at: item.read_at || new Date().toISOString(),
      })),
    );
    setUnreadCount(0);
  };

  const handleScroll = () => {
    const panel = panelRef.current;
    if (!panel || !hasMore || isLoadingMore) return;

    const remaining =
      panel.scrollHeight - panel.scrollTop - panel.clientHeight;
    if (remaining < 48) {
      fetchNotifications(notifications.length);
    }
  };

  const renderNotification = (notification: AppNotification) => {
    const content = (
      <div
        className={`group flex gap-3 border-l-4 p-3 text-left transition ${
          priorityStyles[notification.priority]
        } ${
          notification.read
            ? "bg-white text-gray-600"
            : "bg-[#EEF3FA] text-[#0F2654]"
        }`}
      >
        <span
          className={`mt-2 h-2 w-2 shrink-0 rounded-full ${
            notification.read ? "bg-transparent" : "bg-[#0F2654]"
          }`}
        />
        <div className="min-w-0 flex-1">
          <div
            className={`truncate text-sm ${
              notification.read ? "font-medium" : "font-bold"
            }`}
          >
            {notification.title}
          </div>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-gray-600">
            {notification.message}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-400">
            <span>{formatRelativeTime(notification.created_at)}</span>
            {notification.type === "security" && (
              <span className="rounded-full bg-red-50 px-2 py-0.5 font-medium text-red-700">
                Security
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          aria-label="Delete notification"
          title="Delete notification"
          onClick={(event) => handleDelete(event, notification)}
          className="h-8 w-8 shrink-0 rounded-full text-gray-400 opacity-0 transition hover:bg-white hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
        >
          <Trash2 className="mx-auto h-4 w-4" />
        </button>
      </div>
    );

    return (
      <div
        key={notification.id}
        onClick={() => handleNotificationClick(notification)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            handleNotificationClick(notification);
          }
        }}
        role="button"
        tabIndex={0}
        className="block w-full cursor-pointer"
      >
        {content}
      </div>
    );
  };

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Open notifications"
        title="Notifications"
        onClick={() => setIsOpen((open) => !open)}
        className={`relative flex h-10 items-center justify-center rounded-full text-[#0F2654] transition hover:bg-white/70 ${
          label ? "w-full gap-2 px-4" : "w-10"
        }`}
      >
        <Bell className="h-5 w-5" />
        {label && <span className="text-sm font-semibold">{label}</span>}
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-600 px-1.5 text-center text-xs font-bold leading-5 text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          className={`absolute mt-3 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl ${
            panelAlign === "center"
              ? "left-1/2 -translate-x-1/2"
              : "right-0"
          }`}
        >
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <div>
              <div className="text-sm font-bold text-[#0F2654]">
                Notifications
              </div>
              <div className="text-xs text-gray-500">
                {unreadCount} unread
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                aria-label="Mark all notifications as read"
                title="Mark all as read"
                onClick={handleReadAll}
                disabled={unreadCount === 0}
                className="h-8 w-8 rounded-full text-gray-500 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <CheckCheck className="mx-auto h-4 w-4" />
              </button>
              <button
                type="button"
                aria-label="Close notifications"
                title="Close"
                onClick={() => setIsOpen(false)}
                className="h-8 w-8 rounded-full text-gray-500 transition hover:bg-gray-100"
              >
                <X className="mx-auto h-4 w-4" />
              </button>
            </div>
          </div>

          <div
            ref={panelRef}
            onScroll={handleScroll}
            className="max-h-[26rem] overflow-y-auto"
          >
            {isLoading && notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                Loading notifications
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                No notifications yet
              </div>
            ) : (
              notifications.map(renderNotification)
            )}

            {isLoadingMore && (
              <div className="px-4 py-3 text-center text-xs text-gray-500">
                Loading more
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
