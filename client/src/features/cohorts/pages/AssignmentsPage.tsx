import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { useTerms } from "@features/persona/hooks/useTerms";
import { BTN_GHOST, BTN_PRIMARY } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";
import { cohortDeliveryApi, type AssignmentInput, type Cohort } from "../api/cohortDeliveryApi";
import { dateLabel, DeliveryShell, errorMessage, FIELD, PANEL, useScopeGuard } from "../components/DeliveryShell";
import { MemberPicker, MoreRecords, PagedSelect, useDeliveryPages } from "../components/DeliveryPickers";
import { assignmentCreationKey, completeAssignmentCreation } from "../lib/assignmentIdempotency";

function AssignmentForm({ onCreated }: { onCreated: () => void }) {
  const t = useTerms();
  const router = useRouter();
  const { activeOrganization } = useOrganization();
  const [quizId, setQuizId] = useState("");
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState<"cohort" | "recipients">("cohort");
  const canSelectRecipients = ["owner", "admin", "facilitator"].includes(activeOrganization?.role ?? "");
  const effectiveTarget = canSelectRecipients ? target : "cohort";
  const [cohortId, setCohortId] = useState("");
  const [recipients, setRecipients] = useState<string[]>([]);
  const [availableFrom, setAvailableFrom] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  const [maxAttempts, setMaxAttempts] = useState("1");
  const [minutes, setMinutes] = useState(20);
  const [threshold, setThreshold] = useState(80);
  const [email, setEmail] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const pendingKeys = useRef(new Map<string, string>());
  const submitting = useRef(false);
  const isCurrent = useScopeGuard();
  useEffect(() => {
    if (router.isReady && typeof router.query.cohort === "string") setCohortId(router.query.cohort);
  }, [router.isReady, router.query.cohort]);
  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting.current || !activeOrganization) return;
    if (!quizId || !title.trim() || !closesAt || (effectiveTarget === "cohort" ? !cohortId : !recipients.length)) {
      toast.error("Choose a quiz, title, closing date and recipients."); return;
    }
    const opens = availableFrom ? new Date(availableFrom).getTime() : Date.now();
    const closes = new Date(closesAt).getTime();
    const due = dueAt ? new Date(dueAt).getTime() : null;
    if (!Number.isFinite(closes) || !Number.isFinite(opens) || closes <= Math.max(opens, Date.now()) + minutes * 60_000 || (due != null && (!Number.isFinite(due) || due < opens || due > closes))) {
      toast.error("The availability window must allow a full attempt. Due time must fall within that window."); return;
    }
    const input: AssignmentInput = {
      quiz_id: quizId, title: title.trim(),
      ...(effectiveTarget === "cohort" ? { cohort_id: cohortId } : { recipient_user_ids: recipients }),
      ...(availableFrom ? { available_from: new Date(availableFrom).toISOString() } : {}),
      ...(dueAt ? { due_at: new Date(dueAt).toISOString() } : {}),
      closes_at: new Date(closesAt).toISOString(), max_attempts: maxAttempts === "unlimited" ? null : Number(maxAttempts) as 1 | 2,
      time_limit_minutes: minutes, passing_threshold_percentage: threshold, send_email_invitations: email,
    };
    submitting.current = true;
    setSaving(true);
    try {
      const assignment = await cohortDeliveryApi.createAssignment(input, assignmentCreationKey(pendingKeys.current, input), activeOrganization.organization_id);
      // A confirmed success ends this intent. Failed/unknown outcomes retain
      // their key, while edited payloads get independent retry-safe keys.
      completeAssignmentCreation(pendingKeys.current, input);
      if (!isCurrent()) return;
      setCreatedId(assignment.id);
      toast.success("Assignment created.");
      onCreated();
      try {
        const navigated = await router.push(ROUTES.assignment(assignment.id));
        if (navigated === false && isCurrent()) toast.error("Assignment created. Use the link below to open it.");
      } catch {
        if (isCurrent()) toast.error("Assignment created, but the page could not be opened. Use the link below.");
      }
    } catch (error) { if (isCurrent()) toast.error(errorMessage(error, "Could not create the assignment. Retry unchanged to recover safely.")); }
    finally { submitting.current = false; if (isCurrent()) setSaving(false); }
  };
  return <form className={PANEL} onSubmit={(event) => void create(event)}>
    <h2 className="mb-5 text-xl font-extrabold">Assign {t("quiz")}</h2>
    {createdId && <p role="status" className="mb-5">Assignment created. <Link className="font-bold text-brand underline" href={ROUTES.assignment(createdId)}>Open created assignment</Link></p>}
    <p className="mb-5 text-sm text-ink/70">The quiz content and recipient roster are frozen for this assignment. Later edits do not change its evidence.</p>
    <fieldset disabled={saving} className="space-y-5 disabled:opacity-70">
      <PagedSelect label="Quiz" load={cohortDeliveryApi.quizzes} value={quizId} onChange={setQuizId} identify={(item) => item.id} describe={(item) => item.title} />
      <label className="block font-bold">Assignment title<input className={FIELD} maxLength={180} required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <fieldset className="flex flex-wrap gap-5"><legend className="mb-3 font-bold">Recipients</legend>
        <label className="flex gap-2"><input type="radio" name="target" checked={effectiveTarget === "cohort"} onChange={() => setTarget("cohort")} />A {t("group")}</label>
        {canSelectRecipients && <label className="flex gap-2"><input type="radio" name="target" checked={effectiveTarget === "recipients"} onChange={() => setTarget("recipients")} />Named recipients</label>}
      </fieldset>
      {effectiveTarget === "cohort" ? <PagedSelect<Cohort> label={t("group")} load={cohortDeliveryApi.listCohorts} value={cohortId} onChange={setCohortId} identify={(item) => item.id} describe={(item) => item.name} filter={(item) => item.status === "active" && item.can_assign === true} /> :
        <MemberPicker selected={recipients} onChange={setRecipients} load={cohortDeliveryApi.recipientOptions} />}
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="font-bold">Available from (optional)<input type="datetime-local" className={FIELD} value={availableFrom} onChange={(event) => setAvailableFrom(event.target.value)} /></label>
        <label className="font-bold">Due at (optional)<input type="datetime-local" className={FIELD} value={dueAt} onChange={(event) => setDueAt(event.target.value)} /></label>
        <label className="font-bold">Closes at<input type="datetime-local" required className={FIELD} value={closesAt} onChange={(event) => setClosesAt(event.target.value)} /></label>
        <label className="font-bold">Time limit (minutes)<input type="number" min={1} max={1440} required className={FIELD} value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} /></label>
        <label className="font-bold">Attempts allowed<select className={FIELD} value={maxAttempts} onChange={(event) => setMaxAttempts(event.target.value)}><option value="1">1</option><option value="2">2</option><option value="unlimited">Unlimited</option></select></label>
        <label className="font-bold">Passing threshold (%)<input type="number" min={0} max={100} required className={FIELD} value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} /></label>
      </div>
      <p className="text-sm text-ink/70">Times use your local timezone. The due date marks lateness; closing ends access. Recipients need enough time to finish before closing.</p>
      <label className="flex items-start gap-3"><input type="checkbox" checked={email} onChange={(event) => setEmail(event.target.checked)} />Also email recipients an invitation. Their assignment remains visible in the app regardless.</label>
      <button className={BTN_PRIMARY} disabled={saving}>{saving ? "Creating..." : "Create assignment"}</button>
    </fieldset>
  </form>;
}

function AssignmentsContent() {
  const { activeOrganization } = useOrganization();
  const router = useRouter();
  const page = useDeliveryPages(cohortDeliveryApi.listAssignments);
  const t = useTerms();
  const [showCreate, setShowCreate] = useState(false);
  useEffect(() => {
    if (router.isReady && typeof router.query.cohort === "string") setShowCreate(true);
  }, [router.isReady, router.query.cohort]);
  // Visibility is a convenience, never authorization. Detail capabilities and
  // every mutation remain server-authorized, including cohort delegation.
  const mayAssign = ["owner", "admin", "facilitator"].includes(activeOrganization?.role ?? "") || typeof router.query.cohort === "string";
  return <div className="space-y-6">
    {mayAssign && <button type="button" className={BTN_PRIMARY} onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Hide creation form" : `Assign ${t("quiz")}`}</button>}
    {showCreate && <AssignmentForm onCreated={() => void page.refresh()} />}
    <div className="grid gap-4 sm:grid-cols-2">{page.items.map((assignment) => <Link key={assignment.id} href={ROUTES.assignment(assignment.id)} className={`${PANEL} hover:border-brand`}>
      <p className="text-xs font-bold uppercase tracking-widest text-brand">{assignment.status}</p><h2 className="mt-2 text-xl font-extrabold">{assignment.title}</h2>
      <p className="mt-3 text-sm">Closes {dateLabel(assignment.closes_at)}</p>
    </Link>)}</div>
    {!page.loading && !page.error && !page.items.length && <p className={PANEL}>No assigned {t("quiz", "plural")} are available in this workspace.</p>}
    <MoreRecords {...page} />
    <Link href={ROUTES.MY_ASSIGNMENTS} className={BTN_GHOST}>See assignments for me</Link>
  </div>;
}
export default function AssignmentsPage() {
  const t = useTerms();
  return <DeliveryShell title={`Assigned ${t("quiz", "plural")}`}><AssignmentsContent /></DeliveryShell>;
}
