import { useRef, useState } from "react";
import type { GetServerSideProps } from "next";
import Link from "next/link";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import toast from "react-hot-toast";
import { useTerms } from "@features/persona/hooks/useTerms";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { BTN_GHOST, BTN_PRIMARY } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";
import { cohortDeliveryApi, type Assignment, type AssignmentRecipient } from "../api/cohortDeliveryApi";
import { dateLabel, DeliveryShell, errorMessage, PANEL, percentageLabel, ResourceMessage, useDeliveryResource, useScopeGuard } from "../components/DeliveryShell";
import { MoreRecords, useDeliveryPages } from "../components/DeliveryPickers";

function RecipientAttempts({ assignmentId, userId }: { assignmentId: string; userId: string }) {
  const page = useDeliveryPages((cursor) => cohortDeliveryApi.attempts(assignmentId, userId, cursor));
  return <section className={`${PANEL} mt-4`} aria-label="Recipient attempts"><h3 className="mb-4 font-extrabold">Assigned attempts</h3>
    <ul className="divide-y divide-divider">{page.items.map((attempt) => <li key={attempt.id} className="flex flex-wrap justify-between gap-3 py-3">
      <span>{attempt.status} / {dateLabel(attempt.submitted_at || attempt.completed_at || attempt.started_at)} / {percentageLabel(attempt.percentage)}</span>
      {attempt.status === "submitted" && <Link className="font-bold text-brand underline" href={ROUTES.assignedAttempt(assignmentId, userId, attempt.id)}>View attempt</Link>}
    </li>)}</ul>
    {!page.loading && !page.error && !page.items.length && <p>No attempts have been made for this assignment.</p>}
    <MoreRecords {...page} />
  </section>;
}

function AssignmentRegister({ assignment }: { assignment: Assignment }) {
  const [recipient, setRecipient] = useState<string | null>(null);
  const page = useDeliveryPages<AssignmentRecipient>(async (cursor) => {
    const result = await cohortDeliveryApi.getAssignment(assignment.id, cursor);
    if (result.can_report !== true) {
      throw Object.assign(new Error("Reporting access is no longer available."), {
        response: { status: 403, data: { detail: "Reporting access is no longer available." } },
      });
    }
    return { items: result.recipients ?? [], next_cursor: result.next_cursor ?? null };
  }, { items: assignment.recipients ?? [], next_cursor: assignment.next_cursor ?? null });
  return <section aria-label="Completion register" className={PANEL}>
    <h2 className="text-xl font-extrabold">Completion register</h2><p className="mt-2 text-sm text-ink/70">{assignment.status === "closed" ? "Final completion evidence" : "Provisional progress while the assignment remains open"}</p>
    {assignment.summary_availability === "unavailable" ? <p role="alert" className="my-4">Completion evidence is unavailable. Counts are not shown; contact support.</p> :
      <div className="my-5 grid gap-3 sm:grid-cols-3"><p>Completed: <strong>{assignment.completed_count ?? 0}/{assignment.participant_count ?? 0}</strong></p>
        <p>Outstanding: <strong>{assignment.outstanding_count ?? 0}</strong></p>
        <p>Average: <strong>{percentageLabel(assignment.average_percentage)}</strong></p></div>}
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-3">Recipient</th><th className="p-3">State</th><th className="p-3">Latest result</th><th className="p-3">Completed</th><th className="p-3">Attempts</th></tr></thead>
      <tbody>{page.items.map((row) => <tr key={row.recipient_id} className="border-t border-divider">
        <td className="p-3">{row.recipient_name || row.user_id || "Recipient"}</td><td className="p-3">{row.recipient_status.replace(/_/g, " ")}</td>
        <td className="p-3">{percentageLabel(row.latest_percentage)}</td><td className="p-3">{dateLabel(row.completed_at)}</td>
        <td className="p-3">{row.user_id ? <button type="button" className="font-bold text-brand underline" onClick={() => setRecipient((value) => value === row.user_id ? null : row.user_id)}>View attempts</button> : "Unavailable"}</td>
      </tr>)}</tbody></table>
      {!page.items.length && !page.error && <p className="mt-4">No recipients are recorded.</p>}
    </div>
    <MoreRecords {...page} />
    {recipient && !page.error && <RecipientAttempts key={recipient} assignmentId={assignment.id} userId={recipient} />}
  </section>;
}

function AssignmentDetailContent({ assignmentId }: { assignmentId: string }) {
  const { activeOrganization } = useOrganization();
  const resource = useDeliveryResource(() => cohortDeliveryApi.getAssignment(assignmentId), assignmentId);
  const assignment = resource.value;
  const [confirmation, setConfirmation] = useState(false);
  const [closing, setClosing] = useState(false);
  const busy = useRef(false);
  const isCurrent = useScopeGuard();
  const t = useTerms();
  const close = async () => {
    if (busy.current || !assignment?.can_manage || !activeOrganization) return;
    busy.current = true; setClosing(true);
    try {
      await cohortDeliveryApi.closeAssignment(assignmentId, activeOrganization.organization_id);
      if (!isCurrent()) return;
      setConfirmation(false); resource.refresh(); toast.success("Assignment closed.");
    } catch (error) { if (isCurrent()) toast.error(errorMessage(error, "Could not close this assignment.")); }
    finally { busy.current = false; if (isCurrent()) setClosing(false); }
  };
  if (!assignment) return <ResourceMessage {...resource} retry={resource.refresh} />;
  return <div className="space-y-6">
    <header className={PANEL}><p className="text-xs font-bold uppercase tracking-widest text-brand">{assignment.status}</p><h2 className="mt-2 text-2xl font-extrabold">{assignment.title}</h2>
      <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
        <div><dt className="font-bold">Available from</dt><dd>{dateLabel(assignment.available_from)}</dd></div><div><dt className="font-bold">Due</dt><dd>{dateLabel(assignment.due_at)}</dd></div>
        <div><dt className="font-bold">Closes</dt><dd>{dateLabel(assignment.closes_at)}</dd></div><div><dt className="font-bold">Attempt limit</dt><dd>{assignment.max_attempts ?? "Unlimited"}</dd></div>
        <div><dt className="font-bold">Time limit</dt><dd>{assignment.time_limit_minutes} minutes</dd></div><div><dt className="font-bold">Passing threshold</dt><dd>{assignment.passing_threshold_percentage}%</dd></div>
      </dl><p className="mt-4 break-all text-xs text-ink/60">Frozen quiz revision: {assignment.quiz_revision_id}</p>
      <div className="mt-5 flex flex-wrap gap-3">{assignment.cohort_id && <Link className={BTN_GHOST} href={ROUTES.cohort(assignment.cohort_id)}>View {t("group")}</Link>}
        <button type="button" className={BTN_GHOST} onClick={resource.refresh}>Refresh</button>
        {assignment.can_manage === true && assignment.status === "open" && <button type="button" className={BTN_PRIMARY} onClick={() => setConfirmation(true)}>Close assignment</button>}
      </div>
    </header>
    {assignment.can_report === true ? <AssignmentRegister assignment={assignment} /> : <p className={PANEL}>Reporting permission is separate from assignment management. No recipient results are loaded here.</p>}
    <Dialog open={confirmation} onClose={() => { if (!closing) setConfirmation(false); }} className="relative z-[110]">
      <div className="fixed inset-0 bg-ink/50" aria-hidden="true" /><div className="fixed inset-0 flex items-center justify-center overflow-y-auto p-5"><DialogPanel className={`${PANEL} max-w-xl`}>
        <DialogTitle className="text-xl font-extrabold">Close this assignment permanently?</DialogTitle>
        <p className="my-4">This ends access immediately, stops in-progress attempts, and freezes the completion record. It cannot be reopened.</p>
        <div className="flex flex-wrap gap-3"><button type="button" autoFocus disabled={closing} className={BTN_GHOST} onClick={() => setConfirmation(false)}>Keep open</button>
          <button type="button" disabled={closing} className={BTN_PRIMARY} onClick={() => void close()}>{closing ? "Closing..." : "Close permanently"}</button></div>
      </DialogPanel></div>
    </Dialog>
  </div>;
}
export default function AssignmentDetailPage({ assignmentId }: { assignmentId: string }) {
  return <DeliveryShell title="Assignment workspace"><AssignmentDetailContent key={assignmentId} assignmentId={assignmentId} /></DeliveryShell>;
}
export const getServerSideProps: GetServerSideProps<{ assignmentId: string }> = async ({ params }) => ({ props: { assignmentId: String(params?.assignmentId || "") } });
