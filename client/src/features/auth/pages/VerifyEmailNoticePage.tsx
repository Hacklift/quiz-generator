import { useTranslation } from "react-i18next";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { ROUTES } from "@shared/config/patterns/routes";
import { useAuth } from "@features/auth/context/authContext";
import VerifyEmailModal from "@features/auth/components/VerifyEmailModal";
import toast from "react-hot-toast";

export default function VerifyEmailNoticePage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!user) {
      // Not logged in, redirect to login
      router.push(ROUTES.LOGIN);
      return;
    }

    if (user.is_verified) {
      // Already verified, redirect to profile
      router.push(ROUTES.PROFILE);
      return;
    }

    // Unverified user, show modal
    setShowModal(true);
  }, [user, router]);

  if (!user || user.is_verified) {
    return null; // Will redirect
  }

  return (
    <>
      <div className="flex min-h-screen flex-col bg-gray-50">
        <NavBar />
        <main className="mx-auto flex w-full max-w-3xl flex-1 items-center px-4 py-10">
          <section className="w-full rounded-2xl border border-amber-200 bg-white p-8 shadow-sm">
            <h1 className="text-2xl font-bold text-[#143E6F]">
              {uiText("maec6836d2e5098f0")}
            </h1>
            <p className="mt-3 text-gray-700">{uiText("m419cbf12d5604188")}</p>
          </section>
        </main>
        <Footer />
      </div>

      <VerifyEmailModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          router.push(ROUTES.PROFILE);
        }}
        userEmail={user.email}
        onVerified={async () => {
          toast.success(uiText("m0bae7b45c0c57fd5"));
          await refreshUser?.();
          setShowModal(false);
          router.push(ROUTES.PROFILE);
        }}
      />
    </>
  );
}
