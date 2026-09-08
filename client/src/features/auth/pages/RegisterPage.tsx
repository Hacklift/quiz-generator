import { useState } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "@shared/config/patterns/routes";
import SignUpModal from "@features/auth/components/SignUpModal";
import SignInModal from "@features/auth/components/SignInModal";

const RegisterPage: React.FC = () => {
  const router = useRouter();
  const [showSignUp, setShowSignUp] = useState(true);
  const [showLogin, setShowLogin] = useState(false);

  return (
    <div className="min-h-screen flex justify-center items-center bg-gray-100">
      {/* Always render both modals */}
      <SignUpModal
        isOpen={showSignUp}
        onClose={() => {
          setShowSignUp(false);
          router.push(ROUTES.HOME);
        }}
        switchToSignIn={() => {
          setShowSignUp(false);
          setShowLogin(true);
        }}
        onSuccess={() => {
          setShowSignUp(false);
          router.push(ROUTES.VERIFY_EMAIL); // redirect to verification
        }}
      />

      <SignInModal
        isOpen={showLogin}
        onClose={() => setShowLogin(false)}
        redirectTo={ROUTES.DASHBOARD}
        switchToSignUp={() => {
          setShowLogin(false);
          setShowSignUp(true);
        }}
      />
    </div>
  );
};

export default RegisterPage;
