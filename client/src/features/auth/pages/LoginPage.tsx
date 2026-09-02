import { useState } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "@shared/config/patterns/routes";
import SignInModal from "@features/auth/components/SignInModal";
import SignInButton from "@features/quiz/components/SignInButton";
import { EMAIL_REGEX, PASSWORD_REGEX } from "@shared/config/patterns/patterns";
import { LoginPayload } from "@features/auth/types/User";

export default function LoginPage() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold mb-8 text-center text-[#143E6F]">
        Welcome Back
      </h1>

      {/* Sign In Button */}
      <SignInButton onOpen={() => setIsModalOpen(true)} className="mb-4" />

      {/* Optional: Link to Sign Up */}
      <p className="text-sm text-gray-600 mb-8">
        Don’t have an account?{" "}
        <button
          onClick={() => router.push(ROUTES.REGISTER)}
          className="text-blue-600 hover:underline"
        >
          Register
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
