"use client";
import { useTranslation } from "react-i18next";

import React, { ComponentType } from "react";
import {
  personaGenerateHref,
  type SchoolUserType,
} from "@shared/config/persona";
import { type TerminologyResolver } from "@shared/config/terminology";
import { useTerms } from "@features/persona/hooks/useTerms";
import DashboardShell from "@features/dashboard/components/DashboardShell";
import QuickActions from "@features/dashboard/components/QuickActions";
import RecentQuizzes from "@features/dashboard/components/RecentQuizzes";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import TeacherDashboard from "./views/TeacherDashboard";
import LecturerDashboard from "./views/LecturerDashboard";
import StudentDashboard from "./views/StudentDashboard";
import ParentDashboard from "./views/ParentDashboard";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

/**
 * [SCAFFOLD-OWNED] School category dashboard (#124).
 *
 * Reference implementation for the persona dashboards: category-level
 * chrome (quick actions, recent activity) with the user-type view composed
 * underneath.
 *
 * The dispatch map is written complete so each user-type ticket only ever
 * edits its own leaf file — do not convert it to next/dynamic, the static
 * imports are what make `next build` fail loudly on a missing view.
 */
const SCHOOL_VIEWS: Record<
  SchoolUserType,
  ComponentType<DashboardViewProps>
> = {
  teacher: TeacherDashboard,
  lecturer: LecturerDashboard,
  student: StudentDashboard,
  parent: ParentDashboard,
};

export default function SchoolDashboard({ persona, user }: DashboardViewProps) {
  const { t: uiText } = useTranslation("ui");

  const SCHOOL_COPY: Record<
    SchoolUserType,
    { title: string; lede: (t: TerminologyResolver) => string }
  > = {
    teacher: {
      title: uiText("m80b19a1cbc57552a"),
      lede: (t) =>
        `Set work, run it live, and see how your ${t("learner", "plural")} did.`,
    },
    lecturer: {
      title: uiText("mf24600100b29da55"),
      lede: (t) =>
        `Create focused checks for your ${t("group", "plural")} and review the results.`,
    },
    student: {
      title: uiText("m5c26a05eac3da9f6"),
      lede: (t) =>
        `Build a practice quiz and strengthen your understanding before the next ${t("group")}.`,
    },
    parent: {
      title: uiText("mea454e1a37703a1a"),
      lede: (t) =>
        `Create a short practice quiz to support your ${t("learner")}'s learning at home.`,
    },
  };

  const { categories } = usePersonaCopy();
  const t = useTerms();
  const UserTypeView = SCHOOL_VIEWS[persona.userType as SchoolUserType];
  const copy = SCHOOL_COPY[persona.userType as SchoolUserType];

  const greetingName = user.full_name?.split(" ")[0] || user.username;

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
        <QuickActions
          actions={[
            {
              label: uiText("m642f9e9bfeafeb88", { value0: t("quiz") }),
              description: uiText("mbfb29e4e4e786dab", { value0: t("quiz") }),
              href: personaGenerateHref(persona.userType),
            },
            {
              label: uiText("m0b8eeac901367065", { value0: t("live_quiz") }),
              description: uiText("m218c2b78d68d2979", {
                value0: t("live_quiz"),
              }),
              href: "/quiz-access",
            },
            {
              label: uiText("m64f4f83dc91c5fca"),
              description: uiText("mae0908865ae22343"),
              href: "/popular",
            },
          ]}
        />

        <RecentQuizzes
          heading={uiText("m28ffefc4a23a9747", { value0: t("quiz", "plural") })}
          emptyMessage={uiText("m14ca2b043b020a30", {
            value0: t("quiz"),
            value1: t("group", "plural"),
          })}
        />

        <UserTypeView persona={persona} user={user} />
      </div>
    </DashboardShell>
  );
}
