"use client";

import React, { ComponentType } from "react";
import {
  getCategoryDefinition,
  personaGenerateHref,
  type CorporateUserType,
} from "@shared/config/persona";
import { type TerminologyResolver } from "@shared/config/terminology";
import { useTerms } from "@features/persona/hooks/useTerms";
import DashboardShell from "@features/dashboard/components/DashboardShell";
import QuickActions from "@features/dashboard/components/QuickActions";
import RecentQuizzes from "@features/dashboard/components/RecentQuizzes";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import BusinessDashboard from "./views/BusinessDashboard";
import EmployeeDashboard from "./views/EmployeeDashboard";
import HrDashboard from "./views/HrDashboard";

const CORPORATE_COPY: Record<
  CorporateUserType,
  { title: string; lede: (t: TerminologyResolver) => string }
> = {
  business: {
    title: "Build the next training session.",
    lede: (t) =>
      `Create practical training for your ${t("group", "plural")}, run it live, and keep a clear record of progress.`,
  },
  employee: {
    title: "Keep your learning moving.",
    lede: () =>
      "Build practice quizzes and return to the training that matters to your role.",
  },
  hr: {
    title: "Keep compliance training on track.",
    lede: () =>
      "Create focused training and maintain the records your organisation needs.",
  },
};

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
  const copy = CORPORATE_COPY[persona.userType as CorporateUserType];

  const greetingName = user.full_name?.split(" ")[0] || user.username;
  const quickActions =
    persona.userType === "employee"
      ? [
          {
            label: "Assigned training",
            description: "Start required training, track due dates, and view completed scores.",
            href: "/assigned-training",
          },
          {
            label: `Practice ${t("quiz")}`,
            description: "Generate a private practice quiz for your next skill.",
            href: personaGenerateHref(persona.userType),
          },
        ]
      : [
          {
            label:
              persona.userType === "hr"
                ? "New compliance quiz"
                : `New ${t("quiz")}`,
            description: `Generate a ${t("quiz")} for any training topic, with the answer key included.`,
            href: personaGenerateHref(persona.userType),
          },
          {
            label:
              persona.userType === "hr" ? "Compliance runs" : "Training runs",
            description: "Assign training, share access, and review completion in one workspace.",
            href: `/training-runs?kind=${
              persona.userType === "hr" ? "compliance" : "business"
            }`,
          },
          {
            label: `Run ${t("live_quiz")}`,
            description: "Manage existing live training and review participant activity.",
            href: "/my-live-quizzes",
          },
        ];

  return (
    <DashboardShell
      kicker={getCategoryDefinition(persona.category).label}
      title={`Welcome back, ${greetingName}. ${copy.title}`}
      lede={`${copy.lede(t)} Everything for your ${t("group", "plural")} is in one place.`}
    >
      <div className="flex flex-col gap-[36px]">
        <QuickActions actions={quickActions} />

        <RecentQuizzes
          heading="Recent training activity"
          emptyMessage={`Nothing here yet. Generate your first ${t(
            "quiz",
          )} and it will show up here with your recent training activity.`}
        />

        <UserTypeView persona={persona} user={user} />
      </div>
    </DashboardShell>
  );
}
