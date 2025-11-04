import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "../constants/patterns/routes";
import { useAuth } from "../contexts/authContext";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";

export default function ProfilePage() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push(ROUTES.LOGIN);
    }
  }, [user, isLoading, router]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
      setShowLogoutConfirm(false);
    }
  };

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

  if (!user) return null;

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <NavBar />

      <main className="flex-grow mx-auto px-4 py-8 w-full max-w-6xl">
        <h1 className="text-3xl font-bold text-[#143E6F] mb-8 text-center">
          My Profile
        </h1>

        <div className="bg-white rounded-2xl shadow-sm p-8 mb-6 max-w-3xl mx-auto w-full">
          <div className="flex items-center mb-6">
            <div className="w-20 h-20 rounded-full bg-[#143E6F] flex items-center justify-center text-white text-3xl font-bold">
              {user.username?.charAt(0).toUpperCase() || "U"}
            </div>
            <div className="ml-6">
              <h2 className="text-2xl font-semibold text-gray-900">
                {user.username || "User"}
              </h2>
              <p className="text-gray-500 mt-1">
                {user.email || "No email provided"}
              </p>
            </div>
          </div>

          <div className="border-t pt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Account Information
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-3 border-b">
                <span className="text-gray-600">Username</span>
                <span className="font-medium text-gray-900">
                  {user.username || "N/A"}
                </span>
              </div>
              <div className="flex justify-between items-center py-3 border-b">
                <span className="text-gray-600">Email</span>
                <span className="font-medium text-gray-900">
                  {user.email || "N/A"}
                </span>
              </div>
              <div className="flex justify-between items-center py-3">
                <span className="text-gray-600">Account Status</span>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  Active
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-8 max-w-3xl mx-auto w-full">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Account Actions
          </h3>
          <div className="space-y-3">
            <button
              onClick={() => setShowLogoutConfirm(true)}
              className="w-full text-left px-4 py-3 rounded-lg border border-red-300 hover:bg-red-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-red-600">Logout</p>
                  <p className="text-sm text-red-500">
                    Sign out of your account
                  </p>
                </div>
                <svg
                  className="w-5 h-5 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
              </div>
            </button>
          </div>
        </div>
      </main>

      <Footer />

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
    </div>
  );
}
