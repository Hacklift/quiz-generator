import type { AppProps } from "next/app";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Toaster } from "react-hot-toast";
import SplashScreen from "@app/components/SplashScreen";
import { AuthProvider } from "@features/auth/context/authContext";
import { PersonaProvider } from "@features/persona/context/personaContext";
import PersonaOnboardingGate from "@features/persona/components/PersonaOnboardingGate";
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
      if (process.env.NODE_ENV !== "production") {
        navigator.serviceWorker
          .getRegistrations()
          .then((registrations) =>
            Promise.all(
              registrations.map((registration) => registration.unregister()),
            ),
          )
          .catch((err) => console.error("SW cleanup failed:", err));

        if ("caches" in window) {
          caches
            .keys()
            .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
            .catch((err) => console.error("Cache cleanup failed:", err));
        }
        return;
      }

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
      <PersonaProvider>
        <SplashScreen />
        <EmailVerificationBanner />
        <PersonaOnboardingGate />

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
      </PersonaProvider>
    </AuthProvider>
  );
}
