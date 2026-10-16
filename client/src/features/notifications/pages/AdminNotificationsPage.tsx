"use client";
import { useTranslation } from "react-i18next";

import { FormEvent, useState } from "react";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { useAuth } from "@features/auth/context/authContext";
import {
  broadcastNotification,
  createAdminNotification,
  NotificationType,
} from "@features/notifications/api/notificationsApi";

const notificationTypes: NotificationType[] = [
  "admin",
  "system",
  "security",
  "payment",
];

export default function AdminNotificationsPage() {
  const { t: uiText } = useTranslation("ui");

  const { user, isLoading } = useAuth();
  const [mode, setMode] = useState<"single" | "broadcast">("broadcast");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState("");
  const [formData, setFormData] = useState({
    user_id: "",
    title: "",
    message: "",
    type: "admin" as NotificationType,
    action_url: "",
    expires_at: "",
    active_users_only: true,
  });

  const updateField = (
    field: keyof typeof formData,
    value: string | boolean,
  ) => {
    setFormData((current) => ({ ...current, [field]: value }));
    setResult("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setResult("");

    try {
      const basePayload = {
        title: formData.title.trim(),
        message: formData.message.trim(),
        type: formData.type,
        action_url: formData.action_url.trim() || undefined,
        expires_at: formData.expires_at || undefined,
      };

      if (mode === "single") {
        await createAdminNotification({
          ...basePayload,
          user_id: formData.user_id.trim(),
        });
        setResult("Notification created for the selected user.");
      } else {
        const response = await broadcastNotification({
          ...basePayload,
          active_users_only: formData.active_users_only,
        });
        setResult(
          `Broadcast notification created for ${response.created_count} user${
            response.created_count === 1 ? "" : "s"
          }.`,
        );
      }

      setFormData((current) => ({
        ...current,
        user_id: "",
        title: "",
        message: "",
        action_url: "",
        expires_at: "",
      }));
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail ||
          error?.message ||
          uiText("m4ccbe37d857fd13c"),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <RequireAuth
      title={uiText("mae80505b8ccd7e83")}
      description={uiText("mabcc0825b584c28f")}
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />

        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-3xl">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-[#0F2654]">
                {uiText("mae80505b8ccd7e83")}
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                {uiText("m275acc6b83943109")}
              </p>
            </div>

            {isLoading ? (
              <div className="flex min-h-64 items-center justify-center rounded-lg bg-white">
                <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0F2654]" />
              </div>
            ) : user?.role !== "admin" ? (
              <div className="rounded-lg border border-gray-200 bg-white px-6 py-10 text-center">
                <h2 className="text-xl font-semibold text-[#0F2654]">
                  {uiText("m812fc837108361ba")}
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  {uiText("mec01e5bb3aab2ccc")}
                </p>
              </div>
            ) : (
              <form
                onSubmit={handleSubmit}
                className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="mb-5 grid grid-cols-2 rounded-lg border border-gray-200 bg-gray-50 p-1">
                  <button
                    type="button"
                    onClick={() => setMode("broadcast")}
                    className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                      mode === "broadcast"
                        ? "bg-[#0F2654] text-white"
                        : "text-gray-600 hover:bg-white"
                    }`}
                  >
                    {uiText("m17bc917834360179")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("single")}
                    className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                      mode === "single"
                        ? "bg-[#0F2654] text-white"
                        : "text-gray-600 hover:bg-white"
                    }`}
                  >
                    {uiText("m3a09078a12c067a7")}
                  </button>
                </div>

                <div className="space-y-4">
                  {mode === "single" && (
                    <label className="block">
                      <span className="text-sm font-semibold text-gray-700">
                        {uiText("m7967e089a7b94464")}
                      </span>
                      <input
                        value={formData.user_id}
                        onChange={(event) =>
                          updateField("user_id", event.target.value)
                        }
                        required={mode === "single"}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                      />
                    </label>
                  )}

                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="block">
                      <span className="text-sm font-semibold text-gray-700">
                        {uiText("mbaaddf70fb5d432b")}
                      </span>
                      <select
                        value={formData.type}
                        onChange={(event) =>
                          updateField(
                            "type",
                            event.target.value as NotificationType,
                          )
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm capitalize focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                      >
                        {notificationTypes.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-gray-700">
                        {uiText("mb613b9ece0d42862")}
                      </span>
                      <input
                        type="datetime-local"
                        value={formData.expires_at}
                        onChange={(event) =>
                          updateField("expires_at", event.target.value)
                        }
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                      />
                    </label>
                  </div>

                  <label className="block">
                    <span className="text-sm font-semibold text-gray-700">
                      {uiText("m7e8cd2056da73a7f")}
                    </span>
                    <input
                      value={formData.title}
                      onChange={(event) =>
                        updateField("title", event.target.value)
                      }
                      required
                      maxLength={120}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                    />
                  </label>

                  <label className="block">
                    <span className="text-sm font-semibold text-gray-700">
                      {uiText("m2f77668a9dfbf8d5")}
                    </span>
                    <textarea
                      value={formData.message}
                      onChange={(event) =>
                        updateField("message", event.target.value)
                      }
                      required
                      rows={5}
                      maxLength={1000}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                    />
                  </label>

                  <label className="block">
                    <span className="text-sm font-semibold text-gray-700">
                      {uiText("ma653dec58ff858ec")}
                    </span>
                    <input
                      value={formData.action_url}
                      onChange={(event) =>
                        updateField("action_url", event.target.value)
                      }
                      placeholder="/notifications"
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#0F2654] focus:outline-none focus:ring-1 focus:ring-[#0F2654]"
                    />
                  </label>

                  {mode === "broadcast" && (
                    <label className="flex items-center gap-3 rounded-lg border border-gray-200 px-3 py-3 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={formData.active_users_only}
                        onChange={(event) =>
                          updateField("active_users_only", event.target.checked)
                        }
                        className="h-4 w-4 rounded border-gray-300 text-[#0F2654]"
                      />
                      {uiText("m5d3ed16541506ef5")}
                    </label>
                  )}
                </div>

                {result && (
                  <div className="mt-5 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
                    {result}
                  </div>
                )}

                <div className="mt-6 flex justify-end">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="rounded-lg bg-[#0F2654] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#173773] disabled:cursor-not-allowed disabled:bg-gray-400"
                  >
                    {isSubmitting
                      ? uiText("m286a3af7348e8312")
                      : uiText("m02f68b6356d5c5dc")}
                  </button>
                </div>
              </form>
            )}
          </div>
        </main>

        <Footer />
      </div>
    </RequireAuth>
  );
}
