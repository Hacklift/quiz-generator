"use client";
import { useTranslation } from "react-i18next";

import React, { ComponentType } from "react";
import {
  personaGenerateHref,
  type CorporateUserType,
} from "@shared/config/persona";
import { type TerminologyResolver } from "@shared/config/terminology";
import { useTerms } from "@features/persona/hooks/useTerms";
import DashboardShell from "@features/dashboard/components/DashboardShell";
import QuickActions from "@features/dashboard/components/QuickActions";
import RecentQuizzes from "@features/dashboard/components/RecentQuizzes";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import { ROUTES } from "@shared/config/patterns/routes";
import BusinessDashboard from "./views/BusinessDashboard";
import EmployeeDashboard from "./views/EmployeeDashboard";
import HrDashboard from "./views/HrDashboard";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

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
  const { t: uiText } = useTranslation("ui");

  const CORPORATE_COPY: Record<
    CorporateUserType,
    { title: string; lede: (t: TerminologyResolver) => string }
  > = {
    business: {
      title: uiText("md5b2d2beb7c65ab3"),
      lede: (t) =>
        `Create practical training for your ${t("group", "plural")}, run it live, and keep a clear record of progress.`,
    },
    employee: {
      title: uiText("m8516e3649509fd52"),
      lede: () =>
        "Build practice quizzes and return to the training that matters to your role.",
    },
    hr: {
      title: uiText("ma5cc93c42f439921"),
      lede: () =>
        "Create focused training and maintain the records your organisation needs.",
    },
  };

  const t = useTerms();
  const { categories } = usePersonaCopy();
  const UserTypeView = CORPORATE_VIEWS[persona.userType as CorporateUserType];
  const copy = CORPORATE_COPY[persona.userType as CorporateUserType];

  const greetingName = user.full_name?.split(" ")[0] || user.username;
  const quickActions =
    persona.userType === "employee"
      ? [
          {
            label: uiText("m6bc7e9d5dd0c3d67"),
            description: uiText("m36c79985abaca098"),
            href: ROUTES.ASSIGNED_TRAINING,
          },
          {
            label: uiText("m73240c82afaf24d4", { value0: t("quiz") }),
            description: uiText("mcb7e49e4b0f24fea"),
            href: personaGenerateHref(persona.userType),
          },
        ]
      : [
          {
            label:
              persona.userType === "hr"
                ? "New compliance quiz"
                : `New ${t("quiz")}`,
            description: uiText("m1fc64a1266054ba3", { value0: t("quiz") }),
            href: personaGenerateHref(persona.userType),
          },
          {
            label:
              persona.userType === "hr" ? "Compliance runs" : "Training runs",
            description: uiText("m272076cd2c1eb948"),
            href: `${ROUTES.TRAINING_RUNS}?kind=${
              persona.userType === "hr" ? "compliance" : "business"
            }`,
          },
          {
            label: uiText("m9914ffb7eae7c8cf", { value0: t("live_quiz") }),
            description: uiText("mc13c78d04f69bb87"),
            href: "/my-live-quizzes",
          },
        ];

  return (
    <DashboardShell
      kicker={categories[persona.category].label}
      title={uiText("mbc4cdc1643f5ec38", {
        value0: greetingName,
        value1: copy.title,
      })}
      lede={`${copy.lede(t)} Everything for your ${t("group", "plural")} is in one place.`}
    >
      <div className="flex flex-col gap-[36px]">
        <QuickActions actions={quickActions} />

        <RecentQuizzes
          heading={uiText("mad5bfa74a32be5eb")}
          emptyMessage={uiText("m53791d3b68d40c83", { value0: t("quiz") })}
        />

        <UserTypeView persona={persona} user={user} />
      </div>
    </DashboardShell>
  );
}
