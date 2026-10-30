import { useRef, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import { useTerms } from "@features/persona/hooks/useTerms";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { BTN_GHOST, BTN_PRIMARY } from "@shared/ui/quizwerk";
import { cohortDeliveryApi } from "../api/cohortDeliveryApi";
import { dateLabel, DeliveryShell, errorMessage, PANEL, percentageLabel, useScopeGuard } from "../components/DeliveryShell";
import { MoreRecords, useDeliveryPages } from "../components/DeliveryPickers";

function MyAssignmentsContent() {
  const { activeOrganization } = useOrganization();
  const page = useDeliveryPages(cohortDeliveryApi.myAssignments);
  const [starting, setStarting] = useState<string | null>(null);
  const busy = useRef(false);
  const router = useRouter();
  const t = useTerms();
  const isCurrent = useScopeGuard();
  const start = async (assignmentId: string) => {
    if (busy.current || !activeOrganization) return;
    busy.current = true; setStarting(assignmentId);
    try {
      const response = await cohortDeliveryApi.startAssignment(assignmentId, activeOrganization.organization_id);
      if (!isCurrent()) return;
      saveParticipantToken(response.session_id, response.participant_token);
      await router.push(response.redirect_url);
    } catch (error) { if (isCurrent()) toast.error(errorMessage(error, "Unable to start this assignment. Refresh to check availability.")); }
    finally { busy.current = false; if (isCurrent()) setStarting(null); }
  };
  return <section aria-label="My assignments" className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><p>Complete your assigned {t("quiz", "plural")} within their availability windows.</p><button className={BTN_GHOST} type="button" onClick={() => void page.refresh()} disabled={page.loading}>Refresh</button></div>
    {page.items.map((assignment) => <article key={assignment.id} className={`${PANEL} flex flex-wrap items-center justify-between gap-5`}>
      <div><h2 className="text-xl font-extrabold">{assignment.title}</h2><p className="mt-2 text-sm">{(assignment.recipient_status ?? assignment.status).replace(/_/g, " ")} / {assignment.attempts_used ?? 0}/{assignment.max_attempts ?? "unlimited"} attempts</p>
        <p className="mt-2 text-sm">Available {dateLabel(assignment.available_from)} / Due {dateLabel(assignment.due_at)} / Closes {dateLabel(assignment.closes_at)}</p>
        {assignment.latest_percentage != null && <p className="mt-2 font-bold">Latest result: {percentageLabel(assignment.latest_percentage)}</p>}
      </div>
      {assignment.can_start === true || assignment.can_resume === true ? <button className={`${BTN_PRIMARY} disabled:opacity-50`} disabled={starting !== null} type="button" onClick={() => void start(assignment.id)}>{starting === assignment.id ? "Opening..." : assignment.can_resume ? "Resume assignment" : assignment.attempts_used ? "Retry assignment" : "Start assignment"}</button> : <p className="text-sm font-bold">{assignment.has_completed ? "Completed" : assignment.recipient_status === "in_progress" ? "Attempt in progress" : "Not available to start"}</p>}
    </article>)}
    {!page.loading && !page.error && !page.items.length && <p className={PANEL}>Nothing is assigned to you in this workspace yet.</p>}
    <MoreRecords {...page} />
  </section>;
}
export default function MyAssignmentsPage() {
  return <DeliveryShell title="Assigned to me"><MyAssignmentsContent /></DeliveryShell>;
}
