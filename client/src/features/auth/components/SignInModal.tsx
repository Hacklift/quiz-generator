import { useTranslation } from "react-i18next";
import { useState } from "react";
import { useRouter } from "next/router";
import { login } from "@features/auth/api/authApi";
import { EMAIL_REGEX } from "@shared/config/patterns/patterns";
import { ROUTES } from "@shared/config/patterns/routes";
import { LoginPayload, LoginResponse } from "@features/auth/types/User";
import { useAuth } from "@features/auth/context/authContext";

interface SignInModalProps {
  isOpen: boolean;
  onClose: () => void;
  switchToSignUp: () => void;
  onSuccess?: () => void | Promise<void>;
  redirectTo?: string | null;
}

const SignInModal: React.FC<SignInModalProps> = ({
  isOpen,
  onClose,
  switchToSignUp,
  onSuccess,
  redirectTo = null,
}) => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { login: authLogin } = useAuth();
  const [identifier, setIdentifier] = useState(""); // email or username
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!identifier.trim()) {
      setError(uiText("mf031558bdc90c4aa"));
      return;
    }

    if (!password) {
      setError(uiText("m7aeae1412484f637"));
      return;
    }

    setLoading(true);

    try {
      const payload: LoginPayload = {
        identifier: identifier.trim(),
        password,
      };

      const response: LoginResponse = await login(payload);

      if (response.access_token) {
        await authLogin(response.access_token, response.token_type);

        if (onSuccess) {
          await onSuccess();
        } else if (redirectTo) {
          await router.push(redirectTo);
        }
        onClose();
      } else {
        setError(uiText("m19265efd1ad20af6"));
      }
    } catch (error: any) {
      console.error("Login request failed", error);
      const errorMessage =
        error?.message || "Invalid credentials. Please try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    onClose(); // Close the sign-in modal
    router.push(ROUTES.REQUEST_PASSWORD_RESET || "/request-reset-password");
  };

  const handleClose = () => {
    if (!loading) {
      setIdentifier("");
      setPassword("");
      setError("");
      onClose();
    }
  };

  const isEmail = identifier.includes("@");

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50"
      onClick={handleClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-md p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-2xl font-semibold text-center mb-2 text-[#143E6F]">
          {uiText("mbcc0bcc9140b0c97")}
        </h2>
        <p className="text-sm text-gray-600 text-center mb-6">
          {uiText("mb9173eb6bf777aa1")}
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Email or Username Input */}
          <div className="mb-4">
            <label
              htmlFor="identifier"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {uiText("ma8e8987f236c32e4")}
            </label>
            <input
              id="identifier"
              type="text"
              placeholder={uiText("m019f69123a2e382c")}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={loading}
              aria-label={uiText("m2a347f1933d48350")}
              autoComplete="username"
            />
            {identifier && isEmail && !EMAIL_REGEX.test(identifier) && (
              <p className="text-xs text-amber-600 mt-1">
                {uiText("m0e6faadfd9c96694")}
              </p>
            )}
          </div>

          {/* Password Input */}
          <div className="mb-4">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {uiText("me7cf3ef4f17c3999")}
            </label>
            <input
              id="password"
              type="password"
              placeholder={uiText("mc06bf967017462bb")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={loading}
              aria-label={uiText("me7cf3ef4f17c3999")}
              autoComplete="current-password"
            />
          </div>

          {/* Forgot Password Link */}
          <div className="flex justify-end mb-4">
            <button
              type="button"
              onClick={handleForgotPassword}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-700 hover:underline disabled:opacity-50"
            >
              {uiText("meeca4f80a184d5aa")}
            </button>
          </div>

          {/* Sign In Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#143E6F] text-white py-2.5 rounded-lg hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading
              ? uiText("m1f96f5d016bd94a8")
              : uiText("mbcc0bcc9140b0c97")}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">
              {uiText("m1b545b23fae3997a")}
            </span>
          </div>
        </div>

        {/* Sign Up Link */}
        <button
          type="button"
          onClick={switchToSignUp}
          disabled={loading}
          className="w-full border border-gray-300 text-gray-700 py-2.5 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          {uiText("m0dffe234b44793b6")}
        </button>
      </div>
    </div>
  );
};

export default SignInModal;
