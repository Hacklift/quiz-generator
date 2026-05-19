import { useCallback } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/router";
import { useAuth } from "../contexts/authContext";

export const useRequireVerifiedUser = () => {
  const { user } = useAuth();
  const router = useRouter();

  const requireVerified = useCallback(
    (message = "Please verify your email to continue") => {
      if (user?.is_verified === false) {
        toast.error(message);
        router.push("/auth/verify-email-notice");
        return false;
      }
      return true;
    },
    [router, user],
  );

  return { requireVerified, isVerified: user?.is_verified !== false };
};
