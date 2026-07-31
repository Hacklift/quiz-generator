"use client";

// TODO(#125): Corporate category dashboard.
//
// Build this to mirror school/SchoolDashboard.tsx — that file is the
// reference implementation: DashboardShell + QuickActions + RecentQuizzes,
// with the user-type view composed underneath, all wording via useTerms().
// Suggested actions: New training quiz / Run live session / Assigned to me.
//
// The dispatch map below is [SCAFFOLD-OWNED] and already complete; the
// user-type leaves belong to #130, #131 and #132.
import React, { ComponentType } from "react";
import type { CorporateUserType } from "@shared/config/persona";
import { useTerms } from "@features/persona/hooks/useTerms";
import DashboardShell from "@features/dashboard/components/DashboardShell";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import BusinessDashboard from "./views/BusinessDashboard";
import EmployeeDashboard from "./views/EmployeeDashboard";
import HrDashboard from "./views/HrDashboard";

const CORPORATE_VIEWS: Record<
  CorporateUserType,
  ComponentType<DashboardViewProps>
> = {
  business: BusinessDashboard,
  employee: EmployeeDashboard,
  hr: HrDashboard,
};

export default function CorporateDashboard({
  persona,
  user,
}: DashboardViewProps) {
  const t = useTerms();
  const UserTypeView = CORPORATE_VIEWS[persona.userType as CorporateUserType];

  const greetingName = user.full_name?.split(" ")[0] || user.username;

  return (
    <DashboardShell
      kicker="Corporate"
      title={`Welcome back, ${greetingName}`}
      lede={`Build and run training for your ${t(
        "group",
        "plural",
      )}, and keep the ${t("report", "plural")} to prove it.`}
    >
      <UserTypeView persona={persona} user={user} />
    </DashboardShell>
  );
}
