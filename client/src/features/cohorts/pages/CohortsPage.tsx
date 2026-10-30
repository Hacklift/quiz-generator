import { FormEvent, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { useTerms } from "@features/persona/hooks/useTerms";
import { titleCaseTerm } from "@shared/config/terminology";
import { BTN_PRIMARY } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";
import { cohortDeliveryApi, type Cohort, type CohortInput } from "../api/cohortDeliveryApi";
import { adminRole, DeliveryShell, errorMessage, FIELD, PANEL, useScopeGuard } from "../components/DeliveryShell";
import { MoreRecords, PagedSelect, useDeliveryPages } from "../components/DeliveryPickers";

export function CohortFields({ input, change, cohortId }: { input: CohortInput; change: (input: CohortInput) => void; cohortId?: string }) {
  const t = useTerms();
  return <div className="grid gap-4 sm:grid-cols-2">
    <label className="font-bold">Name<input required maxLength={160} className={FIELD} value={input.name} onChange={(event) => change({ ...input, name: event.target.value })} /></label>
    <label className="font-bold">Kind<select className={FIELD} value={input.kind} onChange={(event) => change({ ...input, kind: event.target.value as CohortInput["kind"] })}>
      <option value="class">Class</option><option value="course">Course</option><option value="team">Team</option><option value="department">Department</option><option value="campaign">Campaign</option>
    </select></label>
    <PagedSelect<Cohort> label={`Parent ${t("group")} (optional)`} load={cohortDeliveryApi.listCohorts} value={input.parent_cohort_id ?? ""}
      onChange={(value) => change({ ...input, parent_cohort_id: value || null })} identify={(item) => item.id} describe={(item) => item.name}
      filter={(item) => item.id !== cohortId && !item.parent_cohort_id && item.status === "active"} />
    <p className="self-center text-sm text-ink/70">One optional parent level only. Membership and assignment recipients are not inherited.</p>
  </div>;
}

function CohortsContent() {
  const t = useTerms();
  const { activeOrganization } = useOrganization();
  const [status, setStatus] = useState<"active" | "archived">("active");
  const [listVersion, setListVersion] = useState(0);
  const [input, setInput] = useState<CohortInput>({ name: "", kind: "class", parent_cohort_id: null });
  const [saving, setSaving] = useState(false);
  const isCurrent = useScopeGuard();
  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (saving || !input.name.trim() || !activeOrganization) return;
    setSaving(true);
    try {
      await cohortDeliveryApi.createCohort({ ...input, name: input.name.trim() }, activeOrganization.organization_id);
      if (!isCurrent()) return;
      setInput({ name: "", kind: "class", parent_cohort_id: null });
      toast.success(`${titleCaseTerm(t("group"))} created.`);
      setStatus("active");
      setListVersion((version) => version + 1);
    } catch (error) {
      if (isCurrent()) toast.error(errorMessage(error, "Could not create this group."));
    } finally { if (isCurrent()) setSaving(false); }
  };
  return <div className="space-y-8">
    {adminRole(activeOrganization?.role) && <form onSubmit={(event) => void create(event)} className={PANEL}>
      <h2 className="mb-5 text-xl font-extrabold">New {t("group")}</h2>
      <CohortFields input={input} change={setInput} />
      <button disabled={saving} className={`${BTN_PRIMARY} mt-5 disabled:opacity-50`}>{saving ? "Creating..." : `Create ${t("group")}`}</button>
    </form>}
    <label className="block max-w-xs font-bold">Show {t("group", "plural")}<select value={status} onChange={(event) => setStatus(event.target.value as "active" | "archived")} className={FIELD}><option value="active">Active</option><option value="archived">Archived</option></select></label>
    <CohortList key={`${status}:${listVersion}`} status={status} />
  </div>;
}

function CohortList({ status }: { status: "active" | "archived" }) {
  const t = useTerms();
  const page = useDeliveryPages((cursor) => cohortDeliveryApi.listCohorts(cursor, status));
  return <><section aria-label={t("group", "plural")} className="grid gap-4 sm:grid-cols-2">
      {page.items.map((cohort) => <Link key={cohort.id} href={ROUTES.cohort(cohort.id)} className={`${PANEL} transition hover:border-brand`}>
        <p className="text-xs font-bold uppercase tracking-widest text-brand">{cohort.kind} / {cohort.status}</p>
        <h2 className="mt-2 text-xl font-extrabold">{cohort.name}</h2><p className="mt-3 text-sm">Open roster and authorized progress</p>
      </Link>)}
    </section>
    {!page.loading && !page.error && !page.items.length && <p className={PANEL}>No {t("group", "plural")} are available in this workspace yet.</p>}
    <MoreRecords {...page} />
  </>;
}
export default function CohortsPage() {
  const t = useTerms();
  return <DeliveryShell title={titleCaseTerm(t("group", "plural"))}><CohortsContent /></DeliveryShell>;
}
