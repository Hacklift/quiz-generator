import { useTranslation } from "react-i18next";
import { useState } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "@shared/config/patterns/routes";
import SignInModal from "@features/auth/components/SignInModal";
import SignInButton from "@features/quiz/components/SignInButton";
import { EMAIL_REGEX, PASSWORD_REGEX } from "@shared/config/patterns/patterns";
import { LoginPayload } from "@features/auth/types/User";

export default function LoginPage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold mb-8 text-center text-[#143E6F]">
        {uiText("m0c3310a647b03717")}
      </h1>

      {/* Sign In Button */}
      <SignInButton onOpen={() => setIsModalOpen(true)} className="mb-4" />

      {/* Optional: Link to Sign Up */}
      <p className="text-sm text-gray-600 mb-8">
        {uiText("m9dd227f9ed37aeda")}{" "}
        <button
          onClick={() => router.push(ROUTES.REGISTER)}
          className="text-blue-600 hover:underline"
        >
          {uiText("mbb7234ec12451361")}
        </button>
      </p>

      {/* Sign In Modal */}
      <SignInModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        redirectTo={ROUTES.DASHBOARD}
        switchToSignUp={() => {
          setIsModalOpen(false);
          router.push(ROUTES.REGISTER);
        }}
      />
    </div>
  );
}
