import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Toaster } from "react-hot-toast";
import SplashScreen from "../components/splash_screen/SplashScreen";
import { AuthProvider } from "../contexts/authContext";
import SignInModal from "../components/auth/SignInModal";
import { ROUTES } from "../constants/patterns/routes";
import EmailVerificationBanner from "../components/auth/EmailVerificationBanner";
import "../components/ui/global.css";

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
