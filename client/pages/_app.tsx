// pages/_app.tsx
import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import { Toaster } from "react-hot-toast";
import SplashScreen from "../components/splash_screen/SplashScreen";
import { AuthProvider } from "../contexts/authContext";
import SignInModal from "../components/auth/SignInModal";
import "../components/ui/global.css";

export default function MyApp({ Component, pageProps }: AppProps) {
  const [showSignInModal, setShowSignInModal] = useState(false);

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

      <Component {...pageProps} openLoginModal={openSignInModal} />

      <SignInModal
        isOpen={showSignInModal}
        onClose={closeSignInModal}
        switchToSignUp={() => {}}
      />

      <Toaster position="top-right" />
    </AuthProvider>
  );
}
