import { useState } from "react";
import { RequestPasswordResetProps } from "../../interfaces/props/RequestPasswordResetProps";
import { requestPasswordReset } from "../../lib";

const RequestPasswordResetModal: React.FC<RequestPasswordResetProps> = ({
  isOpen,
  onClose,
  onRequestSuccess,
}) => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await requestPasswordReset(email);
      setSuccess(true);
      setTimeout(() => {
        onRequestSuccess(email); // Pass email to parent
        onClose();
      }, 1500);
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.message ||
        "Failed to send reset instructions. Please try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setEmail("");
      setError("");
      setSuccess(false);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-md p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-center mb-4 text-[#143E6F]">
          Request Password Reset
        </h2>

        {success ? (
          <div className="text-center py-6">
            <div className="text-green-600 text-5xl mb-4">✓</div>
            <p className="text-gray-700 mb-2 font-medium">Check your email!</p>
            <p className="text-sm text-gray-500 mb-3">
              We&apos;ve sent a 6-digit OTP and reset link to:
            </p>
            <p className="text-sm font-medium text-[#143E6F]">{email}</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-4 text-center">
              Enter your email address and we&apos;ll send you a code to reset
              your password.
            </p>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 px-3 py-2 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                required
                disabled={loading}
                aria-label="Email address"
              />

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
                  disabled={loading}
                  className="flex-1 bg-[#143E6F] text-white py-2 rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#0f2f54] transition-colors"
                >
                  {loading ? "Sending..." : "Send Code"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default RequestPasswordResetModal;
