import { useRouter } from "next/router";
import { useState } from "react";
import { isAxiosError } from "axios";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { organizationsApi } from "@features/organizations/api/organizationsApi";
import { useOrganization } from "@features/organizations/context/organizationContext";

export default function AcceptOrganizationInvitationPage() {
  const router = useRouter();
  const { switchOrganization } = useOrganization();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const token = typeof router.query.token === "string" ? router.query.token : null;

  const accept = async () => {
    if (!token) return;
    setIsSubmitting(true);
    try {
      let result: { organization_id: string } | undefined;
      // A concurrent click or a recoverable worker interruption can leave
      // acceptance lease-claimed briefly. This operation is idempotent, so
      // retry only that explicit transient state with bounded backoff.
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          result = await organizationsApi.acceptInvitation(token);
          break;
        } catch (error) {
          const isLeaseInProgress = isAxiosError(error)
            && error.response?.status === 409
            && error.response.data?.detail === "Invitation acceptance is in progress; retry shortly";
          if (!isLeaseInProgress || attempt === 2) {
            throw error;
          }
          await new Promise<void>((resolve) => window.setTimeout(resolve, 500 * (attempt + 1)));
        }
      }
      if (!result) {
        throw new Error("Invitation acceptance did not return an organization");
      }
      await switchOrganization(result.organization_id);
      toast.success("You joined the organization.");
      await router.replace("/dashboard");
    } catch {
      toast.error("This invitation is invalid, expired, or belongs to another email.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const decline = async () => {
    if (!token) return;
    setIsSubmitting(true);
    try {
      await organizationsApi.declineInvitation(token);
      toast.success("Invitation declined.");
      await router.replace("/dashboard");
    } catch {
      toast.error("This invitation is invalid, expired, or belongs to another email.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <RequireAuth title="Organization invitation" description="Sign in with the invited email to respond.">
      <div className="flex min-h-screen flex-col bg-paper text-ink">
        <NavBar />
        <main className="mx-auto flex w-full max-w-xl flex-1 items-center px-5 py-12">
          <section className="w-full border-2 border-divider bg-paper p-7">
            <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-brand">Organization invitation</p>
            <h1 className="mt-3 text-3xl font-extrabold">Join this workspace?</h1>
            <p className="mt-3 leading-7 text-ink/75">Accepting adds your account to the organization selected by this invitation.</p>
            {!token ? <p className="mt-5 text-sm font-bold text-red-700">The invitation link is incomplete.</p> : <div className="mt-7 flex flex-wrap gap-3"><button type="button" disabled={isSubmitting} onClick={() => void accept()} className="bg-brand px-4 py-2 font-bold text-paper disabled:opacity-60">Accept invitation</button><button type="button" disabled={isSubmitting} onClick={() => void decline()} className="border-2 border-divider px-4 py-2 font-bold disabled:opacity-60">Decline</button></div>}
          </section>
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
