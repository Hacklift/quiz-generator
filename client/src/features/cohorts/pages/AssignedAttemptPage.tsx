import type { GetServerSideProps } from "next";
import Link from "next/link";
import { ROUTES } from "@shared/config/patterns/routes";
import { cohortDeliveryApi } from "../api/cohortDeliveryApi";
import { dateLabel, DeliveryShell, PANEL, percentageLabel, ResourceMessage, useDeliveryResource } from "../components/DeliveryShell";

interface AttemptProps { assignmentId: string; userId: string; sessionId: string }
function AuthorizedAttempt({ assignmentId, userId, sessionId }: AttemptProps) {
  const resource = useDeliveryResource(() => cohortDeliveryApi.attempt(assignmentId, userId, sessionId), `${assignmentId}:${userId}:${sessionId}`);
  const attempt = resource.value;
  if (!attempt) return <ResourceMessage {...resource} retry={resource.refresh} />;
  const results = attempt.graded_answers ?? [];
  return <section className={PANEL}><h2 className="text-xl font-extrabold">Assigned attempt result</h2>
    <p className="my-4">{attempt.status} / {dateLabel(attempt.submitted_at || attempt.completed_at)} / {percentageLabel(attempt.percentage)}</p>
    <ol className="divide-y divide-divider">{results.map((result, index) => <li key={index} className="py-5">
      <p className="text-sm font-bold text-brand">{result.is_correct ? "Correct" : "Incorrect"}</p><h3 className="mt-2 font-extrabold">{index + 1}. {result.question}</h3>
      <p className="mt-3">Submitted answer: {result.selected_answer || "No answer"}</p><p>Correct answer: {result.correct_answer || "Not recorded"}</p>
    </li>)}</ol>
    {!results.length && <p>Question-level results are not available for this attempt.</p>}
  </section>;
}
function AttemptAccess(props: AttemptProps) {
  const access = useDeliveryResource(() => cohortDeliveryApi.getAssignment(props.assignmentId), props.assignmentId);
  if (!access.value) return <ResourceMessage {...access} retry={access.refresh} />;
  if (access.value.can_report !== true) return <p role="alert" className={PANEL}>You do not have permission to view recipient attempts.</p>;
  return <AuthorizedAttempt {...props} />;
}
export default function AssignedAttemptPage(props: AttemptProps) {
  return <DeliveryShell title="Assigned attempt"><Link className="mb-5 inline-block font-bold text-brand underline" href={ROUTES.assignment(props.assignmentId)}>Back to assignment</Link><AttemptAccess key={`${props.assignmentId}:${props.userId}:${props.sessionId}`} {...props} /></DeliveryShell>;
}
export const getServerSideProps: GetServerSideProps<AttemptProps> = async ({ params }) => ({ props: {
  assignmentId: String(params?.assignmentId || ""), userId: String(params?.userId || ""), sessionId: String(params?.sessionId || ""),
} });
