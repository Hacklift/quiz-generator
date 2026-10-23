"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { ROUTES } from "@shared/config/patterns/routes";

interface RequireTrainingManagerProps {
  children: ReactNode;
  access?: "manage" | "report";
}

const canManageTrainingRuns = (role: string | null) =>
  role === "owner" || role === "admin" || role === "facilitator";

const canReadTrainingReports = (role: string | null) =>
  canManageTrainingRuns(role) || role === "auditor";

export default function RequireTrainingManager({
  children,
  access = "manage",
}: RequireTrainingManagerProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { activeOrganization, isLoading: organizationLoading } = useOrganization();
  const isLoading = authLoading || organizationLoading;
  const role = activeOrganization?.role ?? null;
  // Client guards only reflect server-proven membership; every request still
  // rechecks the central backend policy, including resource relationships.
  const isAllowed = access === "report"
    ? canReadTrainingReports(role)
    : canManageTrainingRuns(role);

  useEffect(() => {
    if (isAuthenticated && !isLoading && !isAllowed) {
      void router.replace(ROUTES.DASHBOARD);
    }
  }, [isAllowed, isAuthenticated, isLoading, router]);

  return (
    <RequireAuth
      title="Training runs"
      description="Sign in to create and manage training runs."
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

export { canManageTrainingRuns, canReadTrainingReports };
