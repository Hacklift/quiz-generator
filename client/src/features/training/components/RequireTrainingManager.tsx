"use client";
import { useTranslation } from "react-i18next";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
import { ROUTES } from "@shared/config/patterns/routes";

interface RequireTrainingManagerProps {
  children: ReactNode;
}

const canManageTrainingRuns = (
  category: string | null,
  userType: string | null,
) => category === "corporate" && (userType === "business" || userType === "hr");

export default function RequireTrainingManager({
  children,
}: RequireTrainingManagerProps) {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  // URL and local-storage personas tailor the product, but only the persisted
  // authenticated profile may grant a training-management capability.
  const isAllowed = canManageTrainingRuns(
    user?.persona_category ?? null,
    user?.persona_user_type ?? null,
  );

  useEffect(() => {
    if (isAuthenticated && !isLoading && !isAllowed) {
      void router.replace(ROUTES.DASHBOARD);
    }
  }, [isAllowed, isAuthenticated, isLoading, router]);

  return (
    <RequireAuth
      title={uiText("mf228db69bd02211a")}
      description={uiText("m95450be3d95c6cfc")}
    >
      {isAuthenticated && (isLoading || !isAllowed) ? (
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" />
        </div>
      ) : (
        children
      )}
    </RequireAuth>
  );
}

export { canManageTrainingRuns };
