"use client";

import React, { useState } from "react";
import { useAuth } from "../../contexts/authContext";
import { useNotificationSettings } from "../../contexts/notificationSettingsContext";
import { notify } from "../../components/ui/notifications";

const positions = [
  { value: "top-right", label: "Top Right" },
  { value: "top-left", label: "Top Left" },
  { value: "bottom-right", label: "Bottom Right" },
  { value: "bottom-left", label: "Bottom Left" },
];

const themes = [
  { value: "dark", label: "Dark" },
  { value: "light", label: "Light" },
];

export default function NotificationSettingsPage() {
  const { user, isAuthenticated } = useAuth();
  const { settings, updateSettings, isLoading } = useNotificationSettings();
  const [saving, setSaving] = useState(false);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center px-4">
        <div className="bg-slate-700 rounded-lg shadow-lg p-8 text-center max-w-md">
          <h1 className="text-2xl font-bold text-white mb-4">
            Sign in Required
          </h1>
          <p className="text-slate-300 mb-4">
            Please sign in to manage your notification preferences.
          </p>
          <a
            href="/"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-lg"
          >
            Go Home
          </a>
        </div>
      </div>
    );
  }

  if (isLoading || !settings) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-white text-lg">Loading settings...</div>
      </div>
    );
  }

  const handleToggle = async (key: string, value: boolean) => {
    setSaving(true);
    try {
      await updateSettings({ [key]: value });
      notify.success("Setting updated!");
    } catch (error) {
      notify.error("Failed to update setting");
    } finally {
      setSaving(false);
    }
  };

  const handleDurationChange = async (
    durationType: "short" | "medium" | "long",
    value: number
  ) => {
    setSaving(true);
    try {
      await updateSettings({
        duration: { ...settings.duration, [durationType]: value },
      });
      notify.success("Duration updated!");
    } catch (error) {
      notify.error("Failed to update duration");
    } finally {
      setSaving(false);
    }
  };

  const handleTypeToggle = async (
    typeKey: keyof typeof settings.types,
    value: boolean
  ) => {
    setSaving(true);
    try {
      await updateSettings({
        types: { ...settings.types, [typeKey]: value },
      });
      notify.success("Notification type updated!");
    } catch (error) {
      notify.error("Failed to update notification type");
    } finally {
      setSaving(false);
    }
  };

  const handleSelectChange = async (key: string, value: string) => {
    setSaving(true);
    try {
      await updateSettings({ [key]: value });
      notify.success("Setting updated!");
    } catch (error) {
      notify.error("Failed to update setting");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🔔 Notification Settings
          </h1>
          <p className="text-slate-400">
            Customize how you receive notifications in the quiz app
          </p>
        </div>

        {/* Settings Card */}
        <div className="bg-slate-800 rounded-lg shadow-xl p-8 space-y-8">
          {/* Master Toggle */}
          <div className="border-b border-slate-700 pb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Enable Notifications
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  Turn all notifications on or off
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enabled}
                  onChange={(e) => handleToggle("enabled", e.target.checked)}
                  disabled={saving}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>

          {/* Theme Selection */}
          <div className="border-b border-slate-700 pb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Theme</h2>
            <div className="grid grid-cols-2 gap-3">
              {themes.map((theme) => (
                <button
                  key={theme.value}
                  onClick={() =>
                    handleSelectChange(
                      "theme",
                      theme.value as "dark" | "light"
                    )
                  }
                  disabled={saving}
                  className={`py-3 px-4 rounded-lg font-semibold transition ${
                    settings.theme === theme.value
                      ? "bg-blue-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  } ${saving ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  {theme.label}
                </button>
              ))}
            </div>
          </div>

          {/* Position Selection */}
          <div className="border-b border-slate-700 pb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Position</h2>
            <select
              value={settings.position}
              onChange={(e) => handleSelectChange("position", e.target.value)}
              disabled={saving}
              className="w-full bg-slate-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50"
            >
              {positions.map((pos) => (
                <option key={pos.value} value={pos.value}>
                  {pos.label}
                </option>
              ))}
            </select>
          </div>

          {/* Duration Sliders */}
          <div className="border-b border-slate-700 pb-6">
            <h2 className="text-xl font-semibold text-white mb-6">
              Notification Duration
            </h2>
            <div className="space-y-6">
              {/* Short Duration */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-slate-200">Short (Quick feedback)</label>
                  <span className="text-blue-400 font-semibold">
                    {settings.duration.short}ms
                  </span>
                </div>
                <input
                  type="range"
                  min="1000"
                  max="3000"
                  step="100"
                  value={settings.duration.short}
                  onChange={(e) =>
                    handleDurationChange("short", parseInt(e.target.value))
                  }
                  disabled={saving}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                />
              </div>

              {/* Medium Duration */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-slate-200">
                    Medium (Important info)
                  </label>
                  <span className="text-blue-400 font-semibold">
                    {settings.duration.medium}ms
                  </span>
                </div>
                <input
                  type="range"
                  min="2000"
                  max="8000"
                  step="100"
                  value={settings.duration.medium}
                  onChange={(e) =>
                    handleDurationChange("medium", parseInt(e.target.value))
                  }
                  disabled={saving}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                />
              </div>

              {/* Long Duration */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-slate-200">Long (Errors/Important)</label>
                  <span className="text-blue-400 font-semibold">
                    {settings.duration.long}ms
                  </span>
                </div>
                <input
                  type="range"
                  min="3000"
                  max="10000"
                  step="100"
                  value={settings.duration.long}
                  onChange={(e) =>
                    handleDurationChange("long", parseInt(e.target.value))
                  }
                  disabled={saving}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                />
              </div>
            </div>
          </div>

          {/* Sound Toggle */}
          <div className="border-b border-slate-700 pb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Notification Sound
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  Play a sound when notifications arrive
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.sound}
                  onChange={(e) => handleToggle("sound", e.target.checked)}
                  disabled={saving}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>

          {/* Notification Types */}
          <div>
            <h2 className="text-xl font-semibold text-white mb-4">
              Notification Types
            </h2>
            <div className="space-y-3">
              {/* Success */}
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div>
                  <label className="text-slate-200 font-medium">
                    ✅ Success Notifications
                  </label>
                  <p className="text-slate-400 text-xs mt-1">
                    Show when actions succeed
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.types.success}
                    onChange={(e) =>
                      handleTypeToggle("success", e.target.checked)
                    }
                    disabled={saving}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-green-600"></div>
                </label>
              </div>

              {/* Error */}
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div>
                  <label className="text-slate-200 font-medium">
                    ❌ Error Notifications
                  </label>
                  <p className="text-slate-400 text-xs mt-1">
                    Show when errors occur
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.types.error}
                    onChange={(e) => handleTypeToggle("error", e.target.checked)}
                    disabled={saving}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-600"></div>
                </label>
              </div>

              {/* Warning */}
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div>
                  <label className="text-slate-200 font-medium">
                    ⚠️ Warning Notifications
                  </label>
                  <p className="text-slate-400 text-xs mt-1">
                    Show warnings and alerts
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.types.warning}
                    onChange={(e) =>
                      handleTypeToggle("warning", e.target.checked)
                    }
                    disabled={saving}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-yellow-600"></div>
                </label>
              </div>

              {/* Info */}
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div>
                  <label className="text-slate-200 font-medium">
                    ℹ️ Info Notifications
                  </label>
                  <p className="text-slate-400 text-xs mt-1">
                    Show informational messages
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.types.info}
                    onChange={(e) => handleTypeToggle("info", e.target.checked)}
                    disabled={saving}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {/* Quiz */}
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div>
                  <label className="text-slate-200 font-medium">
                    🎓 Quiz Notifications
                  </label>
                  <p className="text-slate-400 text-xs mt-1">
                    Show quiz feedback (correct/wrong/streak)
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.types.quiz}
                    onChange={(e) => handleTypeToggle("quiz", e.target.checked)}
                    disabled={saving}
                    className="sr-only peer"
                  />
                  <div className="w-10 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Save Status */}
          {saving && (
            <div className="bg-blue-900 border border-blue-700 text-blue-200 px-4 py-3 rounded-lg">
              Saving your preferences...
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-slate-400">
          <p>All changes are saved automatically</p>
        </div>
      </div>
    </div>
  );
}
