import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import { Eye, EyeOff } from "lucide-react";
import { SignUpModalProps } from "@features/auth/types/sign-up-modal-props";
import { registerUser } from "@features/auth/api/authApi";
import { EMAIL_REGEX, PASSWORD_REGEX } from "@shared/config/patterns/patterns";
import { useRouter } from "next/router";
import { ROUTES } from "@shared/config/patterns/routes";
import VerifyEmailModal from "./VerifyEmailModal";
import LanguagePicker from "@features/locale/components/LanguagePicker";
import { useSignupLanguage } from "@features/auth/hooks/useSignupLanguage";
import { LANGUAGES, LOCALE_DISPLAY_NAMES } from "@shared/config/locale";

interface ExtendedSignUpModalProps extends SignUpModalProps {
  onSuccess?: () => void;
}

export default function SignUpModal({
  isOpen,
  onClose,
  switchToSignIn,
  onSuccess,
}: ExtendedSignUpModalProps) {
  const { t: uiText } = useTranslation("ui");
  const { t: authText } = useTranslation();

  const router = useRouter();
  const signupLanguage = useSignupLanguage(isOpen);
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [passwordStrength, setPasswordStrength] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loading && !showVerifyModal) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, loading, onClose, showVerifyModal]);

  useEffect(() => {
    const newErrors: Record<string, string> = {};
    if (username && username.length < 3)
      newErrors.username = authText("auth.username");
    if (fullName && fullName.length < 3)
      newErrors.fullName = authText("auth.fullName");
    if (email && !EMAIL_REGEX.test(email))
      newErrors.email = authText("auth.email");
    if (password && !PASSWORD_REGEX.test(password))
      newErrors.password = authText("auth.password");
    if (confirmPassword && password !== confirmPassword)
      newErrors.confirmPassword = authText("auth.passwordMatch");
    setErrors(newErrors);
  }, [username, fullName, email, password, confirmPassword, authText]);

  useEffect(() => {
    if (!password) {
      setPasswordStrength("");
      return;
    }
    let score = 0;
    if (password.length >= 8) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    if (score <= 1) setPasswordStrength("Weak");
    else if (score === 2) setPasswordStrength("Fair");
    else if (score === 3) setPasswordStrength("Good");
    else setPasswordStrength("Strong");
  }, [password]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (
      Object.keys(errors).length > 0 ||
      signupLanguage.checkingInvitation ||
      signupLanguage.invitationError
    )
      return;
    try {
      setLoading(true);
      await registerUser({
        username,
        email,
        full_name: fullName,
        password,
        preferred_locale: signupLanguage.preference,
        organization_invitation_token:
          signupLanguage.invitationToken || undefined,
      });
      setRegisteredEmail(email);
      setShowVerifyModal(true);
      setUsername("");
      setFullName("");
      setEmail("");
      setPassword("");
      setConfirmPassword("");
      setErrors({});
      setPasswordStrength("");
    } catch (error: any) {
      setErrors({
        global: error?.message || authText("auth.registrationFailed"),
      });
    } finally {
      setLoading(false);
    }
  };

  const getStrengthColor = () => {
    switch (passwordStrength) {
      case "Weak":
        return "text-red-600";
      case "Fair":
        return "text-yellow-600";
      case "Good":
        return "text-blue-600";
      case "Strong":
        return "text-green-600";
      default:
        return "text-gray-400";
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 px-4 py-6"
        onClick={() => {
          if (!loading && !showVerifyModal) {
            onClose();
          }
        }}
      >
        <div
          className="relative max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-8"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="relative">
            <h2 className="text-2xl font-semibold text-center text-[#143E6F] font-serif mb-6">
              {uiText("m47de23586e49d833")}
            </h2>
            <button
              onClick={onClose}
              type="button"
              aria-label={uiText("m69df6eafe61d3a9f")}
              className="absolute right-0 top-0 rounded-full p-1 text-2xl text-gray-400 hover:text-gray-600"
            >
              {uiText("m6e8883d99e3c7fff")}
            </button>
          </div>

          {errors.global && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm p-3 rounded-md mb-4">
              {errors.global}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <section className="mb-6 rounded border border-gray-200 p-3">
              {signupLanguage.invitation && (
                <p className="mb-3 text-sm">
                  {authText("language.signupOrganization", {
                    organization: signupLanguage.invitation.name,
                    language:
                      LOCALE_DISPLAY_NAMES[
                        signupLanguage.invitation.default_locale
                      ] ||
                      LANGUAGES.find(
                        (item) =>
                          item.code ===
                          signupLanguage.invitation?.default_locale,
                      )?.name ||
                      signupLanguage.invitation.default_locale,
                  })}
                </p>
              )}
              {signupLanguage.checkingInvitation && (
                <p role="status">{authText("language.checkingInvitation")}</p>
              )}
              {signupLanguage.invitationError && (
                <p role="alert" className="text-red-600">
                  {authText("language.invitationError")}
                </p>
              )}
              <LanguagePicker
                value={
                  signupLanguage.invitation
                    ? signupLanguage.preference
                    : signupLanguage.preference || "en"
                }
                onChange={signupLanguage.chooseLanguage}
                allowOrganizationDefault={Boolean(signupLanguage.invitation)}
                disabled={
                  loading ||
                  signupLanguage.checkingInvitation ||
                  signupLanguage.invitationError
                }
                label={authText("language.signupLabel")}
              />
              <p className="mt-2 text-xs text-gray-600">
                {authText("language.signupHelp")}
              </p>
            </section>
            <div className="mb-4">
              <label
                className="block text-sm font-medium mb-2"
                htmlFor="username"
              >
                {uiText("mcc8586487a10c3b2")}
              </label>
              <input
                type="text"
                id="username"
                placeholder={uiText("m29cf2de040bd12a6")}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`w-full px-4 py-2 border rounded-md ${
                  errors.username ? "border-red-500" : "border-gray-300"
                }`}
                required
              />
              {errors.username && (
                <p className="text-red-600 text-sm mt-1">{errors.username}</p>
              )}
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2" htmlFor="name">
                {uiText("m8e00cdf71fa7cc76")}
              </label>
              <input
                type="text"
                id="name"
                placeholder={uiText("me45c8aa7db3ffb05")}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={`w-full px-4 py-2 border rounded-md ${
                  errors.fullName ? "border-red-500" : "border-gray-300"
                }`}
                required
              />
              {errors.fullName && (
                <p className="text-red-600 text-sm mt-1">{errors.fullName}</p>
              )}
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2" htmlFor="email">
                {uiText("m09bf25ef30833633")}
              </label>
              <input
                type="email"
                id="email"
                placeholder={uiText("m80d7f158474439dc")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`w-full px-4 py-2 border rounded-md ${
                  errors.email ? "border-red-500" : "border-gray-300"
                }`}
                required
              />
              {errors.email && (
                <p className="text-red-600 text-sm mt-1">{errors.email}</p>
              )}
            </div>

            <div className="mb-4 relative">
              <label
                className="block text-sm font-medium mb-2"
                htmlFor="password"
              >
                {uiText("me7cf3ef4f17c3999")}
              </label>
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                placeholder={uiText("m3d81652794e5a8ce")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full px-4 py-2 border rounded-md pr-10 ${
                  errors.password ? "border-red-500" : "border-gray-300"
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-9 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
              <p className="text-xs text-gray-500 mt-2">
                {uiText("me4abe1cfd4cabfaf")}
              </p>
              {errors.password && (
                <p className="text-red-600 text-sm mt-1">{errors.password}</p>
              )}
              {password && (
                <p className={`text-sm mt-1 ${getStrengthColor()}`}>
                  {uiText("md7c97ff70026de77", {
                    value0: passwordStrength
                      ? authText("auth." + passwordStrength)
                      : "",
                  })}
                </p>
              )}
            </div>

            <div className="mb-6 relative">
              <label
                className="block text-sm font-medium mb-2"
                htmlFor="confirmPassword"
              >
                {uiText("mc292210c44167923")}
              </label>
              <input
                type={showConfirmPassword ? "text" : "password"}
                id="confirmPassword"
                placeholder={uiText("mc292210c44167923")}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`w-full px-4 py-2 border rounded-md pr-10 ${
                  errors.confirmPassword ? "border-red-500" : "border-gray-300"
                }`}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-9 text-gray-500 hover:text-gray-700"
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
              {errors.confirmPassword && (
                <p className="text-red-600 text-sm mt-1">
                  {errors.confirmPassword}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                signupLanguage.checkingInvitation ||
                signupLanguage.invitationError ||
                Object.keys(errors).length > 0
              }
              className="w-full bg-[#143E6F] text-white py-2 rounded-md font-medium mb-6 disabled:opacity-50 hover:bg-[#0f2f54] transition-colors"
            >
              {loading
                ? uiText("m7918d9ac376d6293")
                : uiText("m47de23586e49d833")}
            </button>
          </form>

          <div className="text-center mt-6 text-sm">
            {uiText("m33d3f3055abfb69a")}{" "}
            <button
              onClick={() => {
                onClose();
                switchToSignIn();
              }}
              type="button"
              className="text-gray-400 hover:text-gray-600 underline"
            >
              {uiText("m9d6322c1f4d9d3f3")}
            </button>
          </div>
        </div>
      </div>

      <VerifyEmailModal
        isOpen={showVerifyModal}
        onClose={() => {
          setShowVerifyModal(false);
          onClose();
        }}
        userEmail={registeredEmail}
        onVerified={() => {
          setShowVerifyModal(false);
          if (onSuccess) onSuccess();
          else router.push(ROUTES.LOGIN);
        }}
      />
    </>
  );
}
