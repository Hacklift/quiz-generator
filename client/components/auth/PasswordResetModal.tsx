import { useState, useEffect } from "react";
import { PasswordResetProps } from "../../interfaces/props/PasswordResetProps";
import { resetPassword, requestPasswordReset } from "../../lib";
import { PASSWORD_REGEX } from "../../constants/patterns/patterns";

const PasswordResetModal: React.FC<PasswordResetProps> = ({
  isOpen,
  onClose,
  email: initialEmail = "",
  resetMethod: initialMethod = "otp",
  tokenFromUrl,
  onResetSuccess,
}) => {
  const [email, setEmail] = useState(initialEmail);
  const [method, setMethod] = useState<"otp" | "token">(initialMethod);
  const [otp, setOtp] = useState("");
  const [token, setToken] = useState(tokenFromUrl || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [success, setSuccess] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    if (tokenFromUrl) {
      setMethod("token");
      setToken(tokenFromUrl);
    }
    if (initialEmail) {
      setEmail(initialEmail);
    }
  }, [tokenFromUrl, initialEmail]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(
        () => setResendCooldown(resendCooldown - 1),
        1000,
      );
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  if (!isOpen) return null;

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

  const handleResendOTP = async () => {
    if (!email) {
      setError("Email is required to resend OTP");
      return;
    }

    setResendLoading(true);
    setError("");
    setResendSuccess(false);

    try {
      await requestPasswordReset(email);
      setResendSuccess(true);
      setResendCooldown(60); // 60 seconds cooldown
      setOtp(""); // Clear previous OTP

      setTimeout(() => {
        setResendSuccess(false);
      }, 3000);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.message ||
        "Failed to resend OTP. Please try again.";
      setError(errorMessage);
    } finally {
      setResendLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
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

    setLoading(true);

    try {
      const payload: any = {
        email,
        reset_method: method,
        new_password: newPassword,
      };

      if (method === "otp") {
        payload.otp = otp;
      } else {
        payload.token = token;
      }

      await resetPassword(payload);
      setSuccess(true);

      setTimeout(() => {
        onResetSuccess();
        onClose();
      }, 2000);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        "Failed to reset password. Please check your information and try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  const isFormValid = () => {
    return (
      email &&
      newPassword &&
      confirmPassword &&
      newPassword === confirmPassword &&
      passwordErrors.length === 0 &&
      (method === "otp" ? otp.length === 6 : token)
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-md p-8 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-center mb-2 text-[#143E6F]">
          Reset Your Password
        </h2>

        {method === "otp" && !success && (
          <p className="text-sm text-gray-600 text-center mb-4">
            Enter the 6-digit code sent to your email
          </p>
        )}

        {success ? (
          <div className="text-center py-6">
            <div className="text-green-600 text-5xl mb-4">✓</div>
            <p className="text-gray-700 mb-2 font-medium">
              Password Reset Successful!
            </p>
            <p className="text-sm text-gray-500">
              You can now log in with your new password.
            </p>
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                {error}
              </div>
            )}

            {resendSuccess && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
                New OTP sent successfully! Check your email.
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                  required
                  disabled={loading || !!initialEmail}
                  aria-label="Email address"
                />
              </div>

              {method === "otp" && (
                <>
                  <div className="mb-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Enter OTP
                    </label>
                    <input
                      type="text"
                      value={otp}
                      onChange={(e) =>
                        setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                      placeholder="000000"
                      className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-[#143E6F] text-center text-2xl tracking-widest font-mono"
                      required
                      disabled={loading}
                      maxLength={6}
                      aria-label="One-time password"
                    />
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs text-gray-500">
                        Check your email for the code
                      </p>
                      <button
                        type="button"
                        onClick={handleResendOTP}
                        disabled={
                          resendLoading || resendCooldown > 0 || loading
                        }
                        className="text-xs text-[#143E6F] hover:text-[#0f2f54] hover:underline disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                      >
                        {resendLoading
                          ? "Sending..."
                          : resendCooldown > 0
                            ? `Resend in ${resendCooldown}s`
                            : "Resend OTP"}
                      </button>
                    </div>
                  </div>
                </>
              )}

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
                  aria-label="New password"
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

              <div className="mb-4">
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
                  aria-label="Confirm password"
                />
                {confirmPassword && newPassword !== confirmPassword && (
                  <p className="text-xs text-red-600 mt-1">
                    Passwords do not match
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={loading}
                  className="flex-1 border border-gray-300 text-gray-700 py-2 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !isFormValid()}
                  className="flex-1 bg-[#143E6F] text-white py-2 rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#0f2f54] transition-colors"
                >
                  {loading ? "Resetting..." : "Reset Password"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default PasswordResetModal;
