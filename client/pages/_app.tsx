import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Toaster } from "react-hot-toast";
import SplashScreen from "@app/components/SplashScreen";
import { AuthProvider } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";
import AssistantLauncher from "@features/assistant/components/AssistantLauncher";
import { ROUTES } from "@shared/config/patterns/routes";
import EmailVerificationBanner from "@features/auth/components/EmailVerificationBanner";
import "@shared/styles/global.css";

export default function MyApp({ Component, pageProps }: AppProps) {
  const [showSignInModal, setShowSignInModal] = useState(false);
  const router = useRouter();

  const openSignInModal = () => setShowSignInModal(true);
  const closeSignInModal = () => setShowSignInModal(false);

  useEffect(() => {
    if (typeof window !== "undefined" && "serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker
          .register("/sw.js")
          .then((reg) => console.log("SW registered:", reg.scope))
          .catch((err) => console.error("SW registration failed:", err));
      });
    }
  }, []);

  return (
    <AuthProvider>
      <SplashScreen />
      <EmailVerificationBanner />

      <Component {...pageProps} openLoginModal={openSignInModal} />
      <AssistantLauncher />

      <SignInModal
        isOpen={showSignInModal}
        onClose={closeSignInModal}
        redirectTo={ROUTES.HOME}
        switchToSignUp={() => {
          closeSignInModal();
          router.push(ROUTES.REGISTER);
        }}
      />

      <Toaster position="top-right" />
    </AuthProvider>
  );
}
