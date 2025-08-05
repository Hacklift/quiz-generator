// pages/_app.tsx
import type { AppProps } from "next/app";
import { useEffect } from "react";
import { Toaster } from "react-hot-toast";
import SplashScreen from "../components/splash_screen/SplashScreen"; // ✅ Import splash screen
import "../components/ui/global.css";

export default function MyApp({ Component, pageProps }: AppProps) {
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
    <>
      <SplashScreen /> {/* ✅ Display splash screen at the top */}
      <Component {...pageProps} />
      <Toaster position="top-right" />
    </>
  );
}
