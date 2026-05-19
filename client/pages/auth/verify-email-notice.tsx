import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";
import { ROUTES } from "../../constants/patterns/routes";
import { useAuth } from "../../contexts/authContext";
import VerifyEmailModal from "../../components/auth/VerifyEmailModal";
import toast from "react-hot-toast";

export default function VerifyEmailNoticePage() {
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
              Verify your email to continue
            </h1>
            <p className="mt-3 text-gray-700">Opening verification modal...</p>
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
          toast.success("Email verified successfully");
          await refreshUser?.();
          setShowModal(false);
          router.push(ROUTES.PROFILE);
        }}
      />
    </>
  );
}
