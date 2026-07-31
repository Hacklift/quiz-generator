"use client";

import React, { ComponentType } from "react";
import { personaGenerateHref, type SchoolUserType } from "@shared/config/persona";
import { titleCaseTerm } from "@shared/config/terminology";
import { useTerms } from "@features/persona/hooks/useTerms";
import DashboardShell from "@features/dashboard/components/DashboardShell";
import QuickActions from "@features/dashboard/components/QuickActions";
import RecentQuizzes from "@features/dashboard/components/RecentQuizzes";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import TeacherDashboard from "./views/TeacherDashboard";
import LecturerDashboard from "./views/LecturerDashboard";
import StudentDashboard from "./views/StudentDashboard";
import ParentDashboard from "./views/ParentDashboard";

/**
 * [SCAFFOLD-OWNED] School category dashboard (#124).
 *
 * Reference implementation for the persona dashboards: category-level
 * chrome (quick actions, recent activity) with the user-type view composed
 * underneath. Corporate (#125) should mirror this shape.
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

  const greetingName = user.full_name?.split(" ")[0] || user.username;

  return (
    <DashboardShell
      kicker="School"
      title={`Welcome back, ${greetingName}`}
      lede={`Set work, run it live, and see how your ${t(
        "learner",
        "plural",
      )} did — everything for your ${t("group", "plural")} in one place.`}
    >
      <div className="flex flex-col gap-[36px]">
        <QuickActions
          actions={[
            {
              label: `New ${t("assignment")}`,
              description: `Generate a ${t(
                "assignment",
              )} on any topic, with the answer key included.`,
              href: personaGenerateHref(persona.userType),
            },
            {
              label: `Run a live ${t("session")}`,
              description: `Put a join code on the projector and score your ${t(
                "learner",
                "plural",
              )} in real time.`,
              href: "/my-live-quizzes",
            },
            {
              label: "Revision practice",
              description: "Build a self-marking practice set from a past topic.",
              href: "/popular",
            },
          ]}
        />

        <RecentQuizzes
          heading={`${titleCaseTerm(t("assignment", "plural"))} you made recently`}
          emptyMessage={`Nothing here yet. Generate your first ${t(
            "assignment",
          )} and it will show up here, ready to run with your ${t(
            "group",
            "plural",
          )}.`}
        />

        <UserTypeView persona={persona} user={user} />
      </div>
    </DashboardShell>
  );
}
