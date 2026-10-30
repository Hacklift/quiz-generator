import { FormEvent, useState } from "react";
import type { GetServerSideProps } from "next";
import Link from "next/link";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import toast from "react-hot-toast";
import { useTerms } from "@features/persona/hooks/useTerms";
import { BTN_GHOST, BTN_PRIMARY } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";
import { cohortDeliveryApi, type Cohort, type CohortInput, type CohortMember } from "../api/cohortDeliveryApi";
import { DeliveryShell, errorMessage, FIELD, PANEL, percentageLabel, ResourceMessage, useDeliveryResource, useScopeGuard } from "../components/DeliveryShell";
import { MemberPicker, MoreRecords, useDeliveryPages } from "../components/DeliveryPickers";
import { CohortFields } from "./CohortsPage";

function CohortProgress({ cohortId }: { cohortId: string }) {
  const t = useTerms();
  const page = useDeliveryPages((cursor) => cohortDeliveryApi.progress(cohortId, cursor));
  return <section className={PANEL} aria-label="Completion and progress">
    <h2 className="text-xl font-extrabold">{t("group")} progress</h2>
    <p className="my-3 text-sm text-ink/70">Each assignment uses the roster captured when it was created. Averages use the latest completed percentage per recipient.</p>
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>
      <th className="p-3">Assigned {t("quiz")}</th><th className="p-3">Completed</th><th className="p-3">Completion</th><th className="p-3">Average</th><th className="p-3">Outstanding</th>
    </tr></thead><tbody>{page.items.map((item) => <tr key={item.id} className="border-t border-divider">
      <td className="p-3"><Link className="font-bold text-brand underline" href={ROUTES.assignment(item.id)}>{item.title}</Link></td>
      {item.summary_availability === "unavailable" ? <td colSpan={4} className="p-3">Completion evidence unavailable</td> : <>
        <td className="p-3">{item.completed_count}/{item.participant_count}</td><td className="p-3">{percentageLabel(item.completion_percentage)}</td>
        <td className="p-3">{percentageLabel(item.average_percentage)}</td><td className="p-3">{item.outstanding_count}</td></>}
    </tr>)}</tbody></table></div>
    {!page.loading && !page.error && !page.items.length && <p className="mt-4">No assignments have been made to this {t("group")}.</p>}
    <MoreRecords {...page} />
  </section>;
}

function Roster({ cohort, canManage }: { cohort: Cohort; canManage: boolean }) {
  const page = useDeliveryPages((cursor) => cohortDeliveryApi.listMembers(cohort.id, cursor));
  const [selected, setSelected] = useState<string[]>([]);
  const [role, setRole] = useState<CohortMember["role"]>("member");
  const [canAssign, setCanAssign] = useState(true);
  const [canReport, setCanReport] = useState(true);
  const [busy, setBusy] = useState(false);
  const isCurrent = useScopeGuard();
  const mutate = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    try {
      await action();
      if (!isCurrent()) return;
      toast.success("Roster updated.");
      setSelected([]);
      void page.refresh();
    } catch (error) { if (isCurrent()) toast.error(errorMessage(error, "Could not update the roster.")); }
    finally { if (isCurrent()) setBusy(false); }
  };
  return <section className={PANEL} aria-label="Roster">
    <h2 className="text-xl font-extrabold">Roster</h2>
    <p className="my-3 text-sm text-ink/70">Roster changes do not alter existing assignments. Guardian membership alone does not grant access to attempts.</p>
    <ul className="divide-y divide-divider">{page.items.map((member) => <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 py-4">
      <div><p className="font-bold">{member.name || member.user_id}</p><p className="text-sm text-ink/70">{member.role}{member.role === "facilitator" ? ` / Assign: ${member.can_assign ? "yes" : "no"} / Report: ${member.can_report ? "yes" : "no"}` : ""}</p></div>
      {canManage && cohort.status === "active" && <div className="flex gap-2">
        <button type="button" disabled={busy} className={BTN_GHOST} onClick={() => { setSelected([member.user_id]); setRole(member.role); setCanAssign(member.can_assign); setCanReport(member.can_report); }}>Edit</button>
        <button type="button" disabled={busy} className={BTN_GHOST} onClick={() => void mutate(() => cohortDeliveryApi.removeMember(cohort.id, member.user_id, cohort.organization_id))}>Remove</button>
      </div>}
    </li>)}</ul>
    {!page.loading && !page.error && !page.items.length && <p>No members yet.</p>}
    <MoreRecords {...page} />
    {canManage && cohort.status === "active" && <form className="mt-6 border-t-2 border-divider pt-5" onSubmit={(event) => {
      event.preventDefault();
      if (selected.length === 1) void mutate(() => cohortDeliveryApi.setMember(cohort.id, { user_id: selected[0], role, can_assign: role === "facilitator" && canAssign, can_report: role === "facilitator" && canReport }, cohort.organization_id));
    }}>
      <h3 className="font-extrabold">Add or update a member</h3>
      <MemberPicker selected={selected} onChange={setSelected} multiple={false} />
      <label className="font-bold">Membership role<select className={FIELD} value={role} onChange={(event) => setRole(event.target.value as CohortMember["role"])}>
        <option value="member">Member</option><option value="facilitator">Facilitator</option><option value="guardian">Guardian</option>
      </select></label>
      {role === "facilitator" && <fieldset className="my-4 space-y-3"><legend className="mb-2 font-bold">Independent facilitator permissions</legend>
        <label className="flex gap-3"><input type="checkbox" checked={canAssign} onChange={(event) => setCanAssign(event.target.checked)} />Can assign</label>
        <label className="flex gap-3"><input type="checkbox" checked={canReport} onChange={(event) => setCanReport(event.target.checked)} />Can view progress and attempts</label>
      </fieldset>}
      <button className={`${BTN_PRIMARY} mt-4 disabled:opacity-50`} disabled={busy || selected.length !== 1}>Save membership</button>
    </form>}
  </section>;
}

function CohortDetailContent({ cohortId }: { cohortId: string }) {
  const resource = useDeliveryResource(() => cohortDeliveryApi.getCohort(cohortId), cohortId);
  const t = useTerms();
  const [editing, setEditing] = useState<CohortInput | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [busy, setBusy] = useState(false);
  const isCurrent = useScopeGuard();
  const cohort = resource.value;
  const mutate = async (event?: FormEvent) => {
    event?.preventDefault();
    if (busy || !cohort) return;
    setBusy(true);
    try {
      if (editing) await cohortDeliveryApi.updateCohort(cohortId, { ...editing, name: editing.name.trim() }, cohort.organization_id);
      else await cohortDeliveryApi.archiveCohort(cohortId, cohort.organization_id);
      if (!isCurrent()) return;
      setEditing(null); setConfirmArchive(false); resource.refresh();
    } catch (error) { if (isCurrent()) toast.error(errorMessage(error, "Could not update this group.")); }
    finally { if (isCurrent()) setBusy(false); }
  };
  if (!cohort) return <ResourceMessage {...resource} retry={resource.refresh} />;
  const canManage = cohort.can_manage === true;
  return <div className="space-y-6">
    <header className={PANEL}><p className="text-sm uppercase tracking-wider text-brand">{cohort.kind} / {cohort.status}</p><h2 className="mt-2 text-2xl font-extrabold">{cohort.name}</h2>
      <div className="mt-5 flex flex-wrap gap-3">
        {canManage && cohort.status === "active" && <><button type="button" className={BTN_GHOST} onClick={() => setEditing({ name: cohort.name, kind: cohort.kind, parent_cohort_id: cohort.parent_cohort_id })}>Edit {t("group")}</button>
          <button type="button" className={BTN_GHOST} onClick={() => { setEditing(null); setConfirmArchive(true); }}>Archive {t("group")}</button></>}
        {cohort.can_assign && cohort.status === "active" && <Link href={{ pathname: ROUTES.ASSIGNMENTS, query: { cohort: cohort.id } }} className={BTN_PRIMARY}>Assign {t("quiz")}</Link>}
      </div>
    </header>
    {editing && <form className={PANEL} onSubmit={(event) => void mutate(event)}><CohortFields input={editing} change={setEditing} cohortId={cohort.id} /><div className="mt-5 flex gap-3"><button disabled={busy} className={BTN_PRIMARY}>Save changes</button><button type="button" className={BTN_GHOST} disabled={busy} onClick={() => setEditing(null)}>Cancel</button></div></form>}
    <Dialog open={confirmArchive} onClose={() => { if (!busy) setConfirmArchive(false); }} className="relative z-[110]">
      <div className="fixed inset-0 bg-ink/50" aria-hidden="true" /><div className="fixed inset-0 flex items-center justify-center overflow-y-auto p-5"><DialogPanel className={`${PANEL} max-w-xl`}>
        <DialogTitle className="text-xl font-bold">Archive {cohort.name}?</DialogTitle><p className="my-4">Existing assignment evidence is retained. No new assignments can target this {t("group")}.</p>
        <div className="flex gap-3"><button type="button" autoFocus disabled={busy} className={BTN_GHOST} onClick={() => setConfirmArchive(false)}>Cancel</button><button type="button" disabled={busy} className={BTN_PRIMARY} onClick={() => void mutate()}>Confirm archive</button></div>
      </DialogPanel></div>
    </Dialog>
    <Roster cohort={cohort} canManage={canManage} />
    {cohort.can_report === true ? <CohortProgress cohortId={cohort.id} /> : <p className={PANEL}>Progress requires separate reporting permission.</p>}
  </div>;
}
export default function CohortDetailPage({ cohortId }: { cohortId: string }) {
  const t = useTerms();
  return <DeliveryShell title={`${t("group")} workspace`}><CohortDetailContent key={cohortId} cohortId={cohortId} /></DeliveryShell>;
}
export const getServerSideProps: GetServerSideProps<{ cohortId: string }> = async ({ params }) => ({ props: { cohortId: String(params?.cohortId || "") } });
