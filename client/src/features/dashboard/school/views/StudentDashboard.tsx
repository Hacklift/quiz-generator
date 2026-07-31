"use client";

// TODO(#128): Student dashboard view.
//
// Contract for this file (see features/dashboard/README.md):
//   * It is rendered inside <DashboardShell> by the category dispatcher —
//     render sections, not page chrome.
//   * Every learner/class/team noun comes from useTerms(), never a literal.
//   * Buttons, containers and rules come from @shared/ui/quizwerk.
//   * Edit ONLY this file. Anything marked [SCAFFOLD-OWNED] is shared —
//     raise it in your PR instead of changing it.
//
// Acceptance criteria live on the issue.
import React from "react";
import DashboardPlaceholder from "@features/dashboard/components/DashboardPlaceholder";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

export default function StudentDashboard({ persona }: DashboardViewProps) {
  return (
    <DashboardPlaceholder
      issue={128}
      title="Student dashboard"
      persona={persona}
    />
  );
}
