import { useState } from "react";
import { VerifyEmailModalProps } from "../../interfaces/props/VerifyEmailModalProps";
import { verifyOtp, resendVerification } from "../../lib";

const VerifyEmailModal: React.FC<VerifyEmailModalProps> = ({
  isOpen,
  onClose,
  userEmail,
  onVerified,
}) => {
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [resendLoading, setResendLoading] = useState(false);

  // ✅ Hook placé AVANT le return conditionnel
  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      await verifyOtp(userEmail, otp);
      setSuccessMessage("Email verified successfully!");

      setTimeout(() => {
        onVerified();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "OTP verification failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      await resendVerification(userEmail);
      setSuccessMessage("Verification email resent! Check your inbox.");
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Failed to resend verification email.",
      );
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-md p-8">
        <div className="relative mb-6">
          <h2 className="text-2xl font-semibold text-center text-[#143E6F] font-serif">
            Verify Your Email
          </h2>
          <button
            onClick={onClose}
            className="absolute top-0 right-0 text-gray-400 hover:text-gray-600 text-2xl"
          >
            &times;
          </button>
        </div>

        {/* Instructions avec les 2 méthodes */}
        <div className="mb-6 text-center">
          <p className="text-sm text-gray-600 mb-3">
            We sent a verification email to{" "}
            <span className="font-medium text-[#143E6F]">{userEmail}</span>
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
            <p className="font-medium mb-2">Choose your verification method:</p>
            <ul className="text-left space-y-1 text-xs">
              <li>• Enter the 6-digit OTP code below, OR</li>
              <li>• Click the verification link in your email</li>
            </ul>
          </div>
        </div>

        {/* Messages d'erreur/succès */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-green-600 text-sm">
            {successMessage}
          </div>
        )}

        {/* Formulaire OTP */}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="otp" className="block text-sm font-medium mb-2">
              Enter OTP Code
            </label>
            <input
              id="otp"
              type="text"
              placeholder="Enter 6-digit code"
              value={otp}
              onChange={(e) =>
                setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-md"
              maxLength={6}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading || otp.length !== 6}
            className="w-full bg-[#143E6F] text-white py-2 rounded-md font-medium mb-4 disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Verify with OTP"}
          </button>
        </form>

        {/* Séparateur */}
        <div className="flex items-center mb-4">
          <div className="flex-1 border-t border-gray-300"></div>
          <span className="px-3 text-sm text-gray-500">OR</span>
          <div className="flex-1 border-t border-gray-300"></div>
        </div>

        {/* Resend */}
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-2">
            Didn&apos;t receive the email?
          </p>
          <button
            onClick={handleResend}
            disabled={resendLoading}
            className="text-[#143E6F] hover:text-[#0f2f54] underline text-sm font-medium disabled:opacity-50"
          >
            {resendLoading ? "Sending..." : "Resend Verification Email"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmailModal;
