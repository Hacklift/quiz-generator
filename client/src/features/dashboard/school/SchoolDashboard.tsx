"use client";

import React, { ComponentType } from "react";
import {
  getCategoryDefinition,
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

const SCHOOL_COPY: Record<
  SchoolUserType,
  { title: string; lede: (t: TerminologyResolver) => string }
> = {
  teacher: {
    title: "Plan your next class quiz.",
    lede: (t) =>
      `Set work, run it live, and see how your ${t("learner", "plural")} did.`,
  },
  lecturer: {
    title: "Get your next lecture ready.",
    lede: (t) =>
      `Create focused checks for your ${t("group", "plural")} and review the results.`,
  },
  student: {
    title: "Ready for revision?",
    lede: (t) =>
      `Build a practice quiz and strengthen your understanding before the next ${t("group")}.`,
  },
  parent: {
    title: "Make practice time count.",
    lede: (t) =>
      `Create a short practice quiz to support your ${t("learner")}'s learning at home.`,
  },
};

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
const SCHOOL_VIEWS: Record<SchoolUserType, ComponentType<DashboardViewProps>> = {
  teacher: TeacherDashboard,
  lecturer: LecturerDashboard,
  student: StudentDashboard,
  parent: ParentDashboard,
};

export default function SchoolDashboard({ persona, user }: DashboardViewProps) {
  const t = useTerms();
  const UserTypeView = SCHOOL_VIEWS[persona.userType as SchoolUserType];
  const copy = SCHOOL_COPY[persona.userType as SchoolUserType];

  const greetingName = user.full_name?.split(" ")[0] || user.username;

  return (
    <DashboardShell
      kicker={getCategoryDefinition(persona.category).label}
      title={`Welcome back, ${greetingName}. ${copy.title}`}
      lede={`${copy.lede(t)} Everything for your ${t("group", "plural")} is in one place.`}
    >
      <div className="flex flex-col gap-[36px]">
        <QuickActions
          actions={[
            {
              label: `New ${t("quiz")}`,
              description: `Generate a ${t("quiz")} on any topic, with the answer key included.`,
              href: personaGenerateHref(persona.userType),
            },
            {
              label: `Join ${t("live_quiz")}`,
              description: `Enter an access code to join a ${t("live_quiz")}.`,
              href: "/quiz-access",
            },
            {
              label: "Revision practice",
              description: "Build a self-marking practice set from a past topic.",
              href: "/popular",
            },
          ]}
        />

        <RecentQuizzes
          heading={`Recent ${t("quiz", "plural")}`}
          emptyMessage={`Nothing here yet. Generate your first ${t(
            "quiz",
          )} and it will show up here, ready to use with your ${t(
            "group",
            "plural",
          )}.`}
        />

        <UserTypeView persona={persona} user={user} />
      </div>
    </DashboardShell>
  );
}
