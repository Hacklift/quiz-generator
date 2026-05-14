import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Bell,
  CheckCheck,
  ExternalLink,
  Shield,
  Trash2,
} from "lucide-react";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";
import RequireAuth from "../components/auth/RequireAuth";
import {
  AppNotification,
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
} from "../lib";

const PAGE_SIZE = 20;
type FilterKey = "all" | "unread" | "security";

const formatTimestamp = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
};

const typeLabels = {
  admin: "Admin",
  payment: "Payment",
  security: "Security",
  system: "System",
};

const priorityDot = {
  high: "bg-red-500",
  medium: "bg-[#0F2654]",
  low: "bg-gray-300",
};

const isLoginNotification = (notification: AppNotification) =>
  notification.type === "security" && notification.title === "New Login Detected";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");
  const [error, setError] = useState("");

  const fetchNotifications = useCallback(async (skip = 0) => {
    const isFirstPage = skip === 0;
    if (isFirstPage) {
      setIsLoading(true);
    } else {
      setIsLoadingMore(true);
    }
    setError("");

    try {
      const data = await getNotifications(PAGE_SIZE, skip);
      setUnreadCount(data.unread_count);
      setHasMore(data.has_more);
      setNotifications((current) =>
        isFirstPage
          ? data.notifications
          : [...current, ...data.notifications],
      );
    } catch (err: any) {
      setError(err?.message || "Failed to load notifications.");
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const filteredNotifications = useMemo(() => {
    if (activeFilter === "unread") {
      return notifications.filter((notification) => !notification.read);
    }
    if (activeFilter === "security") {
      return notifications.filter(
        (notification) => notification.type === "security",
      );
    }
    return notifications;
  }, [activeFilter, notifications]);

  const handleMarkAllRead = async () => {
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

  const handleDelete = async (notification: AppNotification) => {
    await deleteNotification(notification.id);
    setNotifications((current) =>
      current.filter((item) => item.id !== notification.id),
    );
    if (!notification.read) {
      setUnreadCount((count) => Math.max(0, count - 1));
    }
  };

  const filterItems: Array<{ key: FilterKey; label: string }> = [
    { key: "all", label: "All" },
    { key: "unread", label: "Unread" },
    { key: "security", label: "Security" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-[#F6F7F9]">
      <NavBar />

      <RequireAuth
        title="Notifications"
        description="Sign in to view your notifications."
      >
        <main className="mx-auto w-full max-w-4xl flex-grow px-4 py-6 sm:px-6">
          <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#0F2654]">
                <Bell className="h-4 w-4" />
                Inbox
              </div>
              <h1 className="text-2xl font-bold text-[#143E6F]">
                Notifications
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                {unreadCount} unread update{unreadCount === 1 ? "" : "s"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-full bg-[#0F2654] px-4 text-sm font-semibold text-white transition hover:bg-[#173773] disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              <CheckCheck className="h-4 w-4" />
              Mark all read
            </button>
          </div>

          <div className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white px-3 py-2 shadow-sm">
            <div className="flex rounded-full bg-gray-100 p-1">
              {filterItems.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveFilter(item.key)}
                  className={`h-8 rounded-full px-3 text-sm font-semibold transition ${
                    activeFilter === item.key
                      ? "bg-white text-[#0F2654] shadow-sm"
                      : "text-gray-500 hover:text-[#0F2654]"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="hidden items-center gap-2 text-xs font-medium text-gray-500 sm:flex">
              <Shield className="h-4 w-4 text-[#0F2654]" />
              Sign-in checks are shown only at login
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
            {isLoading ? (
              <div className="px-4 py-10 text-center text-sm text-gray-500">
                Loading notifications
              </div>
            ) : filteredNotifications.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-gray-500">
                No notifications in this view
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {filteredNotifications.map((notification) => (
                  <article
                    key={notification.id}
                    className={`group grid grid-cols-[auto,1fr,auto] gap-3 px-4 py-3 transition hover:bg-gray-50 ${
                      notification.read ? "" : "bg-[#F8FBFF]"
                    }`}
                  >
                    <span
                      className={`mt-1.5 h-2.5 w-2.5 rounded-full ${
                        notification.read
                          ? "bg-gray-200"
                          : priorityDot[notification.priority]
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h2
                          className={`truncate text-sm text-[#0F2654] ${
                            notification.read ? "font-semibold" : "font-bold"
                          }`}
                        >
                          {notification.title}
                        </h2>
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-500">
                          {typeLabels[notification.type]}
                        </span>
                        {!notification.read && (
                          <span className="rounded-full bg-[#0F2654] px-2 py-0.5 text-[11px] font-semibold text-white">
                            New
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm leading-5 text-gray-600">
                        {notification.message}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <span className="text-xs text-gray-400">
                          {formatTimestamp(notification.created_at)}
                        </span>
                        {notification.action_url && !isLoginNotification(notification) && (
                          <Link
                            href={notification.action_url}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-[#0F2654] hover:underline"
                          >
                            Open related page
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        )}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDelete(notification)}
                      aria-label="Delete notification"
                      title="Delete"
                      className="h-8 w-8 rounded-full text-gray-400 opacity-100 transition hover:bg-red-50 hover:text-red-600 sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100"
                    >
                      <Trash2 className="mx-auto h-4 w-4" />
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>

          {hasMore && activeFilter === "all" && (
            <div className="mt-5 flex justify-center">
              <button
                type="button"
                onClick={() => fetchNotifications(notifications.length)}
                disabled={isLoadingMore}
                className="h-10 rounded-full border border-gray-300 bg-white px-4 text-sm font-semibold text-[#0F2654] transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoadingMore ? "Loading more" : "Load more"}
              </button>
            </div>
          )}
        </main>
      </RequireAuth>

      <Footer />
    </div>
  );
}
