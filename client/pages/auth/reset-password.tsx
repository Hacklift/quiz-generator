import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "../../constants/patterns/routes";
import PasswordResetModal from "../../components/auth/PasswordResetModal";
import { resetPassword } from "../../lib";
import { PASSWORD_REGEX } from "../../constants/patterns/patterns";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { token, email, mode } = router.query;

  const [userEmail, setUserEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    if (router.isReady) {
      if (email && typeof email === "string") {
        setUserEmail(email);
      }

      if (!token && mode === "otp") {
        setIsModalOpen(true);
      }
    }
  }, [router.isReady, token, mode, email]);

  const validatePassword = (password: string): string[] => {
    const errors: string[] = [];

    if (password.length < 8) {
      errors.push("Password must be at least 8 characters long");
    }

    if (!PASSWORD_REGEX.test(password)) {
      errors.push(
        "Password must contain uppercase, lowercase, number, and special character",
      );
    }

    return errors;
  };

  const handlePasswordChange = (value: string) => {
    setNewPassword(value);
    setPasswordErrors(validatePassword(value));
  };

  const handleTokenReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const errors = validatePassword(newPassword);
    if (errors.length > 0) {
      setError(errors.join(". "));
      return;
    }

    if (!token) {
      setError("Invalid reset link. Token is missing.");
      return;
    }

    const emailToUse = userEmail.trim();
    if (!emailToUse) {
      setError("Please enter your email address");
      return;
    }

    setLoading(true);

    try {
      await resetPassword({
        email: emailToUse,
        reset_method: "token",
        new_password: newPassword,
        token: typeof token === "string" ? token : "",
      });

      setSuccess(true);

      setTimeout(() => {
        router.push(ROUTES.LOGIN);
      }, 2000);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        "Failed to reset password. The link may have expired.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    router.push(ROUTES.LOGIN);
  };

  const handleModalSuccess = () => {
    setTimeout(() => {
      router.push(ROUTES.LOGIN);
    }, 2000);
  };

  if (!router.isReady) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (token) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl w-full max-w-md p-8 shadow-lg">
          <h2 className="text-2xl font-semibold text-center mb-2 text-[#143E6F]">
            Set New Password
          </h2>
          <p className="text-sm text-gray-600 text-center mb-6">
            Create a strong password for your account
          </p>

          {success ? (
            <div className="text-center py-6">
              <div className="text-green-600 text-5xl mb-4">✓</div>
              <p className="text-gray-700 mb-2 font-medium">
                Password Reset Successful!
              </p>
              <p className="text-sm text-gray-500">Redirecting to login...</p>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleTokenReset}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-[#143E6F] text-gray-900"
                    required
                    disabled={loading}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {userEmail
                      ? "Email verified from link"
                      : "Enter the email you used to request the reset"}
                  </p>
                </div>

                <div className="mb-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    placeholder="Enter new password"
                    className={`w-full border px-3 py-2 rounded focus:outline-none focus:ring-2 ${
                      passwordErrors.length > 0 && newPassword
                        ? "border-red-300 focus:ring-red-500"
                        : "border-gray-300 focus:ring-[#143E6F]"
                    }`}
                    required
                    disabled={loading}
                  />
                  {newPassword && passwordErrors.length > 0 && (
                    <div className="mt-1">
                      {passwordErrors.map((err, idx) => (
                        <p key={idx} className="text-xs text-red-600">
                          • {err}
                        </p>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className={`w-full border px-3 py-2 rounded focus:outline-none focus:ring-2 ${
                      confirmPassword && newPassword !== confirmPassword
                        ? "border-red-300 focus:ring-red-500"
                        : "border-gray-300 focus:ring-[#143E6F]"
                    }`}
                    required
                    disabled={loading}
                  />
                  {confirmPassword && newPassword !== confirmPassword && (
                    <p className="text-xs text-red-600 mt-1">
                      Passwords do not match
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={
                    loading ||
                    passwordErrors.length > 0 ||
                    !newPassword ||
                    !confirmPassword ||
                    newPassword !== confirmPassword ||
                    !userEmail
                  }
                  className="w-full bg-[#143E6F] text-white py-2.5 rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#0f2f54] transition-colors"
                >
                  {loading ? "Resetting Password..." : "Reset Password"}
                </button>
              </form>

              <div className="mt-4 text-center">
                <button
                  onClick={() => router.push(ROUTES.LOGIN)}
                  className="text-sm text-gray-600 hover:text-[#143E6F] hover:underline"
                >
                  Back to Login
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  const modalEmail = typeof email === "string" ? email : "";

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <PasswordResetModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        email={modalEmail}
        resetMethod="otp"
        onResetSuccess={handleModalSuccess}
      />
    </div>
  );
}
