import { useTranslation } from "react-i18next";
import { useState } from "react";
import { VerifyEmailModalProps } from "@features/auth/types/VerifyEmailModalProps";
import { verifyOtp, resendVerification } from "@features/auth/api/authApi";

const VerifyEmailModal: React.FC<VerifyEmailModalProps> = ({
  isOpen,
  onClose,
  userEmail,
  onVerified,
}) => {
  const { t: uiText } = useTranslation("ui");

  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [resendLoading, setResendLoading] = useState(false);

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
      setError(err.response?.data?.detail || uiText("m748de674c8df3499"));
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
      setError(err.response?.data?.detail || uiText("mdf7531f70e039e48"));
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white rounded-2xl w-full max-w-md p-8">
        <div className="relative mb-6">
          <h2 className="text-2xl font-semibold text-center text-[#143E6F] font-serif">
            {uiText("m4880bcb6faa527e7")}
          </h2>
          <button
            onClick={onClose}
            className="absolute top-0 right-0 text-gray-400 hover:text-gray-600 text-2xl"
          >
            {uiText("m6e8883d99e3c7fff")}
          </button>
        </div>

        {/* Instructions avec les 2 méthodes */}
        <div className="mb-6 text-center">
          <p className="text-sm text-gray-600 mb-3">
            {uiText("mc9d629e85fdb4e3e")}{" "}
            <span className="font-medium text-[#143E6F]">{userEmail}</span>
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
            <p className="font-medium mb-2">{uiText("m611eb397057e4455")}</p>
            <ul className="text-left space-y-1 text-xs">
              <li>{uiText("mc38acdd567e2cfe8")}</li>
              <li>{uiText("m9d85af73d916bc19")}</li>
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
              {uiText("m5f6da93c0673246e")}
            </label>
            <input
              id="otp"
              type="text"
              placeholder={uiText("mb6cdda8122fb9e2e")}
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
            {loading
              ? uiText("m2ec1ac7d45e8079b")
              : uiText("m001630c71477de4c")}
          </button>
        </form>

        {/* Séparateur */}
        <div className="flex items-center mb-4">
          <div className="flex-1 border-t border-gray-300"></div>
          <span className="px-3 text-sm text-gray-500">
            {uiText("m829e5b28af38ab33")}
          </span>
          <div className="flex-1 border-t border-gray-300"></div>
        </div>

        {/* Resend */}
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-2">
            {uiText("mfe3ac3ada82e4723")}
          </p>
          <button
            onClick={handleResend}
            disabled={resendLoading}
            className="text-[#143E6F] hover:text-[#0f2f54] underline text-sm font-medium disabled:opacity-50"
          >
            {resendLoading
              ? uiText("m286a3af7348e8312")
              : uiText("m5173cc04ffbea7c6")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmailModal;
