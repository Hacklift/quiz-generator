import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import {
  organizationsApi,
  type OrganizationInvitation,
  type OrganizationMember,
} from "@features/organizations/api/organizationsApi";
import { useOrganization } from "@features/organizations/context/organizationContext";

const INVITATION_ROLES = ["admin", "author", "facilitator", "learner", "guardian", "auditor"] as const;

export default function OrganizationManagementPage() {
  const { activeOrganization, switchOrganization } = useOrganization();
  const [organizationName, setOrganizationName] = useState("");
  const [organizationKind, setOrganizationKind] = useState<"school" | "tutoring" | "corporate">("school");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<(typeof INVITATION_ROLES)[number]>("learner");
  const [invitations, setInvitations] = useState<OrganizationInvitation[]>([]);
  const [nextInvitationCursor, setNextInvitationCursor] = useState<string | null>(null);
  const [isLoadingMoreInvitations, setIsLoadingMoreInvitations] = useState(false);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [nextMemberCursor, setNextMemberCursor] = useState<string | null>(null);
  const [isLoadingMoreMembers, setIsLoadingMoreMembers] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [resendingInvitationId, setResendingInvitationId] = useState<string | null>(null);
  const canManage = activeOrganization?.role === "owner" || activeOrganization?.role === "admin";
  const canCreateOrganization = Boolean(activeOrganization);
  const canInvite = canManage && activeOrganization?.organization_kind !== "personal";

  useEffect(() => {
    if (!canInvite) {
      setInvitations([]);
      setMembers([]);
      setNextInvitationCursor(null);
      setNextMemberCursor(null);
      return;
    }
    setNextInvitationCursor(null);
    void Promise.all([organizationsApi.listInvitations(), organizationsApi.listMembers()])
      .then(([invitationPage, memberPage]) => {
        setInvitations(invitationPage.items);
        setNextInvitationCursor(invitationPage.next_cursor);
        setMembers(memberPage.items);
        setNextMemberCursor(memberPage.next_cursor);
      })
      .catch(() => {
      toast.error("Unable to load organization invitations.");
      });
  }, [activeOrganization?.organization_id, canInvite]);

  const loadMoreInvitations = async () => {
    if (!nextInvitationCursor || isLoadingMoreInvitations) return;
    setIsLoadingMoreInvitations(true);
    try {
      const page = await organizationsApi.listInvitations(nextInvitationCursor);
      setInvitations((current) => [
        ...current,
        ...page.items.filter((item) => !current.some((existing) => existing.id === item.id)),
      ]);
      setNextInvitationCursor(page.next_cursor);
    } catch {
      toast.error("Unable to load more invitations.");
    } finally {
      setIsLoadingMoreInvitations(false);
    }
  };

  const loadMoreMembers = async () => {
    if (!nextMemberCursor || isLoadingMoreMembers) return;
    setIsLoadingMoreMembers(true);
    try {
      const page = await organizationsApi.listMembers(nextMemberCursor);
      setMembers((current) => [
        ...current,
        ...page.items.filter((item) => !current.some((existing) => existing.user_id === item.user_id)),
      ]);
      setNextMemberCursor(page.next_cursor);
    } catch {
      toast.error("Unable to load more members.");
    } finally {
      setIsLoadingMoreMembers(false);
    }
  };

  const createOrganization = async (event: FormEvent) => {
    event.preventDefault();
    if (!organizationName.trim()) return;
    setIsCreating(true);
    try {
      const organization = await organizationsApi.createOrganization({
        name: organizationName.trim(),
        kind: organizationKind,
      });
      await switchOrganization(organization.organization_id);
      setOrganizationName("");
      toast.success("Organization created and selected.");
    } catch {
      toast.error("Unable to create the organization.");
    } finally {
      setIsCreating(false);
    }
  };

  const invite = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim()) return;
    setIsInviting(true);
    try {
      const invitation = await organizationsApi.invite({ email: email.trim(), role });
      setInvitations((current) => [invitation, ...current.filter((item) => item.id !== invitation.id)]);
      setEmail("");
      if (invitation.email_delivery_status === "failed") {
        toast.error("Invitation was created, but email delivery failed. Please resend it.");
      } else {
        toast.success("Invitation sent.");
      }
    } catch {
      toast.error("Unable to create this invitation.");
    } finally {
      setIsInviting(false);
    }
  };

  const resendInvitation = async (invitation: OrganizationInvitation) => {
    setResendingInvitationId(invitation.id);
    try {
      const resent = await organizationsApi.invite({
        email: invitation.email,
        role: invitation.role,
      });
      setInvitations((current) => [resent, ...current.filter((item) => item.id !== resent.id)]);
      if (resent.email_delivery_status === "failed") {
        toast.error("Invitation was renewed, but email delivery failed again.");
      } else {
        toast.success("Invitation resent.");
      }
    } catch {
      toast.error("Unable to resend this invitation.");
    } finally {
      setResendingInvitationId(null);
    }
  };

  const revoke = async (invitationId: string) => {
    try {
      const invitation = await organizationsApi.revokeInvitation(invitationId);
      setInvitations((current) => current.map((item) => item.id === invitation.id ? invitation : item));
      toast.success("Invitation revoked.");
    } catch {
      toast.error("Unable to revoke this invitation.");
    }
  };

  const updateMemberStatus = async (
    userId: string,
    nextStatus: "active" | "suspended" | "removed",
  ) => {
    try {
      await organizationsApi.updateMemberStatus(userId, nextStatus);
      setMembers((current) => current.map((member) => (
        member.user_id === userId ? { ...member, status: nextStatus } : member
      )));
      toast.success(
        nextStatus === "active"
          ? "Member reactivated."
          : nextStatus === "suspended"
            ? "Member suspended."
            : "Member removed.",
      );
    } catch {
      toast.error("Unable to update this member.");
    }
  };

  return (
    <RequireAuth title="Organizations" description="Sign in to manage your organizations.">
      <div className="flex min-h-screen flex-col bg-paper text-ink">
        <NavBar />
        <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-12">
          <Link href="/dashboard" className="text-sm font-bold text-brand hover:underline">Back to dashboard</Link>
          <p className="mt-7 text-xs font-extrabold uppercase tracking-[0.14em] text-brand">Organization settings</p>
          <h1 className="mt-3 text-3xl font-extrabold">Workspaces and invitations</h1>
          <p className="mt-3 max-w-2xl leading-7 text-ink/75">Your personal workspace stays private. Create a shared workspace before inviting a school, tutoring, or corporate team.</p>

          {canCreateOrganization ? (
            <form onSubmit={(event) => void createOrganization(event)} className="mt-8 border-2 border-divider p-5">
              <h2 className="text-lg font-extrabold">Create a shared organization</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_180px_auto]">
                <input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} maxLength={160} placeholder="Organization name" className="border-2 border-divider bg-paper px-3 py-2" />
                <select value={organizationKind} onChange={(event) => setOrganizationKind(event.target.value as typeof organizationKind)} className="border-2 border-divider bg-paper px-3 py-2">
                  <option value="school">School</option><option value="tutoring">Tutoring</option><option value="corporate">Corporate</option>
                </select>
                <button disabled={isCreating} className="bg-brand px-4 py-2 font-extrabold text-paper disabled:opacity-60">Create</button>
              </div>
            </form>
          ) : null}

          {activeOrganization ? (
            <section className="mt-8 border-2 border-divider p-5">
              <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-ink/60">Active organization</p>
              <h2 className="mt-2 text-xl font-extrabold">{activeOrganization.organization_name}</h2>
              <p className="mt-1 text-sm text-ink/70">{activeOrganization.organization_kind} workspace · {activeOrganization.role}</p>
              {activeOrganization.organization_kind === "personal" ? <p className="mt-4 text-sm leading-6 text-ink/75">Personal workspaces cannot be shared. Create or switch to a shared organization to invite members.</p> : null}
            </section>
          ) : null}

          {canInvite ? (
            <section className="mt-8 border-2 border-divider p-5">
              <h2 className="text-lg font-extrabold">Invite a member</h2>
              <form onSubmit={(event) => void invite(event)} className="mt-4 grid gap-3 sm:grid-cols-[1fr_170px_auto]">
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="person@example.com" className="border-2 border-divider bg-paper px-3 py-2" />
                <select value={role} onChange={(event) => setRole(event.target.value as typeof role)} className="border-2 border-divider bg-paper px-3 py-2">
                  {INVITATION_ROLES.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                <button disabled={isInviting} className="bg-brand px-4 py-2 font-extrabold text-paper disabled:opacity-60">Invite</button>
              </form>
              <div className="mt-6 space-y-3">
                {invitations.length ? invitations.map((invitation) => (
                  <div key={invitation.id} className="flex flex-wrap items-center justify-between gap-3 border-t-2 border-divider pt-3 text-sm">
                    <span>
                      <strong>{invitation.email}</strong> · {invitation.role} · {invitation.status}
                      {invitation.email_delivery_status === "failed" ? " · delivery failed" : ""}
                    </span>
                    {invitation.status === "invited" ? <span className="flex gap-3">
                      <button type="button" disabled={resendingInvitationId === invitation.id} onClick={() => void resendInvitation(invitation)} className="font-bold text-brand hover:underline disabled:opacity-60">{resendingInvitationId === invitation.id ? "Resending..." : "Resend"}</button>
                      <button type="button" onClick={() => void revoke(invitation.id)} className="font-bold text-red-700 hover:underline">Revoke</button>
                    </span> : null}
                  </div>
                )) : <p className="text-sm text-ink/65">No invitations have been sent from this organization.</p>}
                {nextInvitationCursor ? <button type="button" disabled={isLoadingMoreInvitations} onClick={() => void loadMoreInvitations()} className="pt-2 text-sm font-bold text-brand hover:underline disabled:opacity-60">{isLoadingMoreInvitations ? "Loading invitations..." : "Load more invitations"}</button> : null}
              </div>
              <div className="mt-8 border-t-2 border-divider pt-5">
                <h3 className="text-base font-extrabold">Members</h3>
                <p className="mt-1 text-sm text-ink/65">Suspend access temporarily or remove a member from this organization.</p>
                <div className="mt-4 space-y-3">
                  {members.length ? members.map((member) => (
                    <div key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 border-t-2 border-divider pt-3 text-sm">
                      <span>
                        <strong>{member.full_name || member.username || member.email || "Unknown member"}</strong>
                        {member.email ? ` · ${member.email}` : ""}
                        {` · ${member.role} · ${member.status}`}
                      </span>
                      {member.role !== "owner" && member.status === "active" ? (
                        <span className="flex gap-3">
                          <button type="button" onClick={() => void updateMemberStatus(member.user_id, "suspended")} className="font-bold text-amber-800 hover:underline">Suspend</button>
                          <button type="button" onClick={() => void updateMemberStatus(member.user_id, "removed")} className="font-bold text-red-700 hover:underline">Remove</button>
                        </span>
                      ) : null}
                      {member.role !== "owner" && member.status === "suspended" ? (
                        <span className="flex gap-3">
                          <button type="button" onClick={() => void updateMemberStatus(member.user_id, "active")} className="font-bold text-brand hover:underline">Reactivate</button>
                          <button type="button" onClick={() => void updateMemberStatus(member.user_id, "removed")} className="font-bold text-red-700 hover:underline">Remove</button>
                        </span>
                      ) : null}
                    </div>
                  )) : <p className="text-sm text-ink/65">No active members have joined this organization yet.</p>}
                </div>
                {nextMemberCursor ? <button type="button" disabled={isLoadingMoreMembers} onClick={() => void loadMoreMembers()} className="pt-4 text-sm font-bold text-brand hover:underline disabled:opacity-60">{isLoadingMoreMembers ? "Loading members..." : "Load more members"}</button> : null}
              </div>
            </section>
          ) : null}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
