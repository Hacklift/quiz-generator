import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { Settings } from "lucide-react";
import { useAuth } from "../contexts/authContext";
import {
  updateProfile,
  requestEmailChange,
  verifyEmailChange,
  deleteAccount,
} from "../lib";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";
import RequireAuth from "../components/auth/RequireAuth";

export default function ProfilePage() {
  const { user, isLoading, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [emailChangePending, setEmailChangePending] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [publicProfile, setPublicProfile] = useState(false);
  const [activeSettingSection, setActiveSettingSection] = useState<
    "account" | "profile" | null
  >(null);

  const [formData, setFormData] = useState({
    full_name: "",
    bio: "",
    location: "",
    website: "",
    avatar_color: "#143E6F",
  });

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || "",
        bio: user.bio || "",
        location: user.location || "",
        website: user.website || "",
        avatar_color: user.avatar_color || "#143E6F",
      });
    }
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedPublicProfile = localStorage.getItem("public_profile_enabled");
    if (storedPublicProfile) {
      setPublicProfile(storedPublicProfile === "true");
    }
  }, []);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
      setShowLogoutConfirm(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSaveError("");
  };

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setSaveError("");
    setSaveSuccess(false);

    try {
      await updateProfile(formData);
      setSaveSuccess(true);
      setIsEditing(false);

      if (refreshUser) {
        await refreshUser();
      }
      if (typeof window !== "undefined") {
        localStorage.setItem(
          "public_profile_enabled",
          publicProfile ? "true" : "false",
        );
      }

      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error: any) {
      setSaveError(error.message || "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRequestPasswordReset = () => {
    router.push("/auth/request-reset-password");
  };

  const handleUpdateEmail = async () => {
    if (!newEmail.trim()) {
      toast.error("Please enter a new email.");
      return;
    }
    try {
      await requestEmailChange(newEmail.trim());
      setEmailChangePending(true);
      toast.success("Verification code sent to the new email.");
    } catch (error: any) {
      toast.error(error?.message || "Failed to send verification email.");
    }
  };

  const handleVerifyEmailChange = async () => {
    if (!emailOtp.trim()) {
      toast.error("Enter the verification code.");
      return;
    }
    try {
      await verifyEmailChange(emailOtp.trim());
      setEmailChangePending(false);
      setEmailOtp("");
      setNewEmail("");
      await refreshUser();
      toast.success("Email updated successfully.");
    } catch (error: any) {
      toast.error(error?.message || "Failed to verify email.");
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await deleteAccount();
      setShowDeleteConfirm(false);
      await logout();
    } catch (error: any) {
      toast.error(error?.message || "Failed to delete account.");
    }
  };

  const handleCancelEdit = () => {
    if (user) {
      setFormData({
        full_name: user.full_name || "",
        bio: user.bio || "",
        location: user.location || "",
        website: user.website || "",
        avatar_color: user.avatar_color || "#143E6F",
      });
    }
    setIsEditing(false);
    setSaveError("");
  };

  const avatarColors = [
    "#143E6F",
    "#2563eb",
    "#7c3aed",
    "#db2777",
    "#dc2626",
    "#ea580c",
    "#ca8a04",
    "#16a34a",
    "#0891b2",
    "#6366f1",
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#143E6F]"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <NavBar />

      <RequireAuth
        title="My Profile"
        description="Sign in to view and manage your profile."
      >
        <main className="flex-grow mx-auto px-4 py-8 w-full max-w-6xl">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-[#143E6F]">My Profile</h1>
            <button
              onClick={() => {
                setIsSettingsOpen((prev) => !prev);
                setActiveSettingSection(null);
              }}
              className="p-2 rounded-full border border-gray-200 text-[#143E6F] hover:bg-gray-50 transition-colors"
              aria-label="Open settings"
            >
              <Settings size={20} />
            </button>
          </div>

          {saveSuccess && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
              <svg
                className="w-5 h-5 text-green-600 mr-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-green-800">
                Profile updated successfully!
              </span>
            </div>
          )}

          {saveError && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
              <svg
                className="w-5 h-5 text-red-600 mr-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span className="text-red-800">{saveError}</span>
            </div>
          )}

          <div className="bg-white rounded-2xl shadow-sm p-8 mb-6 max-w-3xl mx-auto w-full">
            <div className="flex items-start mb-6">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center text-white text-3xl font-bold flex-shrink-0"
                style={{ backgroundColor: formData.avatar_color }}
              >
                {user?.username?.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="ml-6 flex-grow">
                {isEditing ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Full Name
                      </label>
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder="Enter your full name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Avatar Color
                      </label>
                      <div className="flex gap-2 flex-wrap">
                        {avatarColors.map((color) => (
                          <button
                            key={color}
                            type="button"
                            onClick={() =>
                              setFormData((prev) => ({
                                ...prev,
                                avatar_color: color,
                              }))
                            }
                            className={`w-10 h-10 rounded-full transition-transform ${
                              formData.avatar_color === color
                                ? "ring-2 ring-offset-2 ring-[#143E6F] scale-110"
                                : "hover:scale-105"
                            }`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900">
                      {formData.full_name || user?.username || "User"}
                    </h2>
                    <p className="text-gray-500 mt-1">
                      @{user?.username || "user"}
                    </p>
                    <p className="text-gray-600 mt-2">
                      {user?.email || "No email provided"}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t pt-6 mb-6">
              {isEditing ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bio
                  </label>
                  <textarea
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                    placeholder="Tell us about yourself..."
                    maxLength={500}
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    {formData.bio.length}/500 characters
                  </p>
                </div>
              ) : (
                formData.bio && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Bio
                    </h3>
                    <p className="text-gray-700">{formData.bio}</p>
                  </div>
                )
              )}
            </div>

            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                {isEditing ? "Edit Information" : "Information"}
              </h3>
              <div className="space-y-4">
                {isEditing ? (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Location
                      </label>
                      <input
                        type="text"
                        name="location"
                        value={formData.location}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder="City, Country"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Website
                      </label>
                      <input
                        type="url"
                        name="website"
                        value={formData.website}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder="https://yourwebsite.com"
                      />
                    </div>
                  </>
                ) : (
                  <>
                    {formData.location && (
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-gray-400 mr-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                        </svg>
                        <span className="text-gray-700">
                          {formData.location}
                        </span>
                      </div>
                    )}
                    {formData.website && (
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-gray-400 mr-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                          />
                        </svg>
                        <a
                          href={formData.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#143E6F] hover:underline"
                        >
                          {formData.website}
                        </a>
                      </div>
                    )}
                  </>
                )}

                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">Username</span>
                  <span className="font-medium text-gray-900">
                    {user?.username || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">Email</span>
                  <span className="font-medium text-gray-900">
                    {user?.email || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">Account Status</span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                </div>
              </div>
            </div>

            {isEditing && (
              <div className="border-t pt-6 mt-6 flex gap-3">
                <button
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                  className="flex-1 bg-[#143E6F] text-white py-2.5 rounded-lg font-medium hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSaving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}
          </div>

          {isSettingsOpen && (
            <div className="bg-white rounded-2xl shadow-sm p-8 max-w-4xl mx-auto w-full space-y-8">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  Settings
                </h3>
                <p className="text-sm text-gray-500">
                  Manage your profile and account.
                </p>
              </div>

              <div className="space-y-4">
                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "profile" ? null : "profile",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-[#143E6F]">
                      Edit Profile
                    </h4>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "profile" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "profile" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Name
                        </label>
                        <input
                          type="text"
                          name="full_name"
                          value={formData.full_name}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Bio
                        </label>
                        <textarea
                          name="bio"
                          value={formData.bio}
                          onChange={handleInputChange}
                          rows={4}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Avatar color
                        </label>
                        <div className="flex gap-2 flex-wrap">
                          {avatarColors.map((color) => (
                            <button
                              key={color}
                              type="button"
                              onClick={() =>
                                setFormData((prev) => ({
                                  ...prev,
                                  avatar_color: color,
                                }))
                              }
                              className={`w-9 h-9 rounded-full border-2 ${
                                formData.avatar_color === color
                                  ? "border-[#143E6F]"
                                  : "border-transparent"
                              }`}
                              style={{ backgroundColor: color }}
                            />
                          ))}
                        </div>
                      </div>
                      <button
                        onClick={handleSaveProfile}
                        disabled={isSaving}
                        className="w-full bg-[#143E6F] text-white py-2 rounded-lg hover:bg-[#0f2f54] transition-colors disabled:opacity-50"
                      >
                        {isSaving
                          ? "Saving..."
                          : saveSuccess
                            ? "Saved"
                            : "Save profile settings"}
                      </button>
                    </div>
                  )}
                </div>

                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "account" ? null : "account",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-[#143E6F]">
                      Account
                    </h4>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "account" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "account" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-4">
                      <button
                        onClick={handleRequestPasswordReset}
                        className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                      >
                        <p className="font-medium text-gray-900">
                          Change password
                        </p>
                        <p className="text-sm text-gray-500">
                          Send a password reset link to your email.
                        </p>
                      </button>

                      <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                        <label className="block text-sm font-medium text-gray-700">
                          Update email (with verification)
                        </label>
                        <input
                          type="email"
                          value={newEmail}
                          onChange={(event) => setNewEmail(event.target.value)}
                          placeholder="new@email.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                        <button
                          onClick={handleUpdateEmail}
                          className="w-full bg-[#143E6F] text-white py-2 rounded-lg hover:bg-[#0f2f54] transition-colors"
                        >
                          Send verification
                        </button>
                        {emailChangePending && (
                          <div className="space-y-2">
                            <input
                              type="text"
                              value={emailOtp}
                              onChange={(event) =>
                                setEmailOtp(event.target.value)
                              }
                              placeholder="Enter verification code"
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                            />
                            <button
                              onClick={handleVerifyEmailChange}
                              className="w-full border border-[#143E6F] text-[#143E6F] py-2 rounded-lg hover:bg-[#143E6F]/10 transition-colors"
                            >
                              Verify email
                            </button>
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => setShowDeleteConfirm(true)}
                        className="w-full text-left px-4 py-3 rounded-lg border border-red-300 hover:bg-red-50 transition-colors"
                      >
                        <p className="font-medium text-red-600">
                          Delete account
                        </p>
                        <p className="text-sm text-red-500">
                          Permanently remove your account and all associated
                          data.
                        </p>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>

        {showLogoutConfirm && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => !isLoggingOut && setShowLogoutConfirm(false)}
          >
            <div
              className="bg-white rounded-2xl w-full max-w-md p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold text-center mb-4 text-gray-900">
                Confirm Logout
              </h2>
              <p className="text-gray-600 text-center mb-6">
                Are you sure you want to logout?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowLogoutConfirm(false)}
                  disabled={isLoggingOut}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="flex-1 bg-[#143E6F] text-white py-2.5 rounded-lg font-medium hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoggingOut ? "Logging out..." : "Logout"}
                </button>
              </div>
            </div>
          </div>
        )}
        {showDeleteConfirm && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <div
              className="bg-white rounded-2xl w-full max-w-md p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold text-center mb-4 text-gray-900">
                Delete Account
              </h2>
              <p className="text-gray-600 text-center mb-6">
                This will permanently remove your account and quizzes. This
                action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  className="flex-1 bg-red-600 text-white py-2.5 rounded-lg font-medium hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </RequireAuth>

      <Footer />
    </div>
  );
}
