import { useTranslation } from "react-i18next";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { resendVerification } from "@features/auth/api/authApi";
import { useAuth } from "@features/auth/context/authContext";
import VerifyEmailModal from "@features/auth/components/VerifyEmailModal";

const RESEND_COOLDOWN_SECONDS = 60;

export default function EmailVerificationBanner() {
  const { t: uiText } = useTranslation("ui");

  const { user, refreshUser } = useAuth();

  const [dismissed, setDismissed] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [showModal, setShowModal] = useState(false);

  const isUnverified = useMemo(
    () => Boolean(user && user.is_verified === false),
    [user],
  );

  // ⏱ cooldown timer
  useEffect(() => {
    if (cooldown <= 0 || !isUnverified || dismissed) return;

    const timer = setTimeout(() => {
      setCooldown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [cooldown, dismissed, isUnverified]);

  if (!isUnverified || dismissed) return null;

  // 📩 Resend email
  const onResend = async () => {
    if (!user?.email || cooldown > 0) return;

    setIsSending(true);
    try {
      await resendVerification(user.email);
      toast.success(uiText("m6ab97e1ce3c2fbb4"));
      setCooldown(RESEND_COOLDOWN_SECONDS);

      // 🔥 IMPORTANT: open modal after resend
      setShowModal(true);
    } catch (error: any) {
      toast.error(error?.message || uiText("mdfdf0fa4a9f62181"));
    } finally {
      setIsSending(false);
    }
  };

  // ✅ Open modal directly, ensuring email is sent
  const onVerifyNow = async () => {
    if (!user?.email) return;

    try {
      await resendVerification(user.email);
      setShowModal(true);
    } catch (error: any) {
      toast.error(error?.message || uiText("mefda09d8f45d1228"));
    }
  };

  return (
    <>
      {/* 🔶 Banner */}
      <div className="sticky top-0 z-[120] w-full border-b border-amber-300 bg-amber-100 px-4 py-3 shadow-sm">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3">
          <p className="text-sm font-medium text-amber-900">
            {uiText("m50087a01463186c7")}
          </p>

          <div className="flex items-center gap-2">
            {/* Resend */}
            <button
              type="button"
              onClick={onResend}
              disabled={isSending || cooldown > 0}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {cooldown > 0
                ? uiText("m7a12bdae3df95a90", { value0: cooldown })
                : isSending
                  ? uiText("m286a3af7348e8312")
                  : uiText("m7c0d0df78303a31d")}
            </button>

            {/* Verify Now */}
            <button
              type="button"
              onClick={onVerifyNow}
              className="rounded-md border border-amber-700 px-3 py-1.5 text-sm font-semibold text-amber-900 transition hover:bg-amber-200"
            >
              {uiText("m1dccacb53bb2adf7")}
            </button>

            {/* Dismiss */}
            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="rounded-md px-2 py-1 text-sm text-amber-900 transition hover:bg-amber-200"
            >
              {uiText("m48845bff334a50a5")}
            </button>
          </div>
        </div>
      </div>

      {/*Verification Modal*/}
      <VerifyEmailModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        userEmail={user?.email || ""}
        onVerified={async () => {
          toast.success(uiText("m0bae7b45c0c57fd5"));

          await refreshUser?.();

          setShowModal(false);
          setDismissed(true);
        }}
      />
    </>
  );
}
