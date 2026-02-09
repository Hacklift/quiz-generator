import { useState } from "react";
import { useRouter } from "next/router";
import { login } from "../../lib";
import { EMAIL_REGEX } from "../../constants/patterns/patterns";
import { ROUTES } from "../../constants/patterns/routes";
import { LoginPayload, LoginResponse } from "../../interfaces/models/User";
import { useAuth } from "../../contexts/authContext";

interface SignInModalProps {
  isOpen: boolean;
  onClose: () => void;
  switchToSignUp: () => void;
}

const SignInModal: React.FC<SignInModalProps> = ({
  isOpen,
  onClose,
  switchToSignUp,
}) => {
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
      setError("Email or username is required");
      return;
    }

    if (!password) {
      setError("Password is required");
      return;
    }

    setLoading(true);

    try {
      const payload: LoginPayload = {
        identifier: identifier.trim(),
        password,
      };

      const response: LoginResponse = await login(payload);

      if (response.access_token && response.refresh_token) {
        await authLogin(
          response.access_token,
          response.refresh_token,
          response.token_type,
        );

        router.push(ROUTES.PROFILE || "/profile");
        onClose();
      } else {
        setError("Invalid response from server");
      }
    } catch (error: any) {
      const errorMessage =
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        "Invalid credentials. Please try again.";
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
          Sign In
        </h2>
        <p className="text-sm text-gray-600 text-center mb-6">
          Welcome back! Please sign in to continue.
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
              Email or Username
            </label>
            <input
              id="identifier"
              type="text"
              placeholder="email@example.com or username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={loading}
              aria-label="Email or username"
              autoComplete="username"
            />
            {identifier && isEmail && !EMAIL_REGEX.test(identifier) && (
              <p className="text-xs text-amber-600 mt-1">
                This doesn&apos;t look like a valid email address
              </p>
            )}
          </div>

          {/* Password Input */}
          <div className="mb-4">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={loading}
              aria-label="Password"
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
              Forgot Password?
            </button>
          </div>

          {/* Sign In Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#143E6F] text-white py-2.5 rounded-lg hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">
              Don&apos;t have an account?
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
          Create Account
        </button>
      </div>
    </div>
  );
};

export default SignInModal;
