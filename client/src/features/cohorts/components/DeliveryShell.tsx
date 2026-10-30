import { ReactNode, useEffect, useRef, useState } from "react";
import Link from "next/link";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
import { useOrganization } from "@features/organizations/context/organizationContext";
import { useTerms } from "@features/persona/hooks/useTerms";
import { titleCaseTerm } from "@shared/config/terminology";
import { ROUTES } from "@shared/config/patterns/routes";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { BTN_GHOST, CONTAINER, Kicker } from "@shared/ui/quizwerk";

export const FIELD = "mt-2 block w-full border-2 border-divider bg-paper p-3 text-ink focus:border-brand focus:outline-none";
export const PANEL = "border-2 border-divider bg-paper p-5 sm:p-7";
export const adminRole = (role?: string) => role === "owner" || role === "admin";
export function errorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}
export const dateLabel = (value?: string | null) => value ? new Date(value).toLocaleString() : "Not set";
export const percentageLabel = (value?: number | null) => value == null ? "No completed attempts" : `${Math.round(value * 10) / 10}%`;

// Check both identity and workspace at completion time, not only effect cleanup.
export function useScopeGuard() {
  const { scopeKey, activeOrganization, isLoading } = useOrganization();
  const { user, isAuthenticated } = useAuth();
  const key = `${user?.id}:${scopeKey}:${activeOrganization?.organization_id}`;
  const current = useRef({ key, ready: false });
  const mounted = useRef(true);
  current.current = { key, ready: isAuthenticated && !isLoading && Boolean(activeOrganization) };
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  return () => mounted.current && current.current.ready && current.current.key === key;
}

export function useDeliveryResource<T>(load: () => Promise<T>, resourceKey: string) {
  const [value, setValue] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const loader = useRef(load);
  loader.current = load;
  const guard = useScopeGuard();
  const guardRef = useRef(guard);
  guardRef.current = guard;
  useEffect(() => {
    let cancelled = false;
    const isCurrent = guardRef.current;
    setValue(null);
    setLoading(true);
    setError(null);
    void loader.current().then((result) => {
      if (!cancelled && isCurrent()) setValue(result);
    }).catch((failure: unknown) => {
      if (!cancelled && isCurrent()) setError(errorMessage(failure, "Unable to load this page. Please try again."));
    }).finally(() => {
      if (!cancelled && isCurrent()) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [resourceKey, version]);
  return { value, loading, error, refresh: () => setVersion((v) => v + 1), setValue };
}

export function DeliveryShell({ children, title }: { children: ReactNode; title: string }) {
  const organization = useOrganization();
  const t = useTerms();
  return <RequireAuth title={title} description="Sign in to use your organization's learning workspace.">
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <NavBar />
      <main className={`${CONTAINER} flex-1 py-10`}>
        <Kicker>{organization.activeOrganization?.organization_name || "Learning workspace"}</Kicker>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
        <nav aria-label="Learning workspace" className="my-6 flex flex-wrap gap-3 border-b-2 border-divider pb-6">
          <Link href={ROUTES.COHORTS} className={BTN_GHOST}>{titleCaseTerm(t("group", "plural"))}</Link>
          <Link href={ROUTES.ASSIGNMENTS} className={BTN_GHOST}>Assigned {t("quiz", "plural")}</Link>
          <Link href={ROUTES.MY_ASSIGNMENTS} className={BTN_GHOST}>Assigned to me</Link>
        </nav>
        {organization.isLoading ? <p role="status">Loading workspace...</p> : !organization.activeOrganization ?
          <p role="alert">No active workspace is available. Open organization settings to resolve your access.</p> :
          <div key={`${organization.scopeKey}:${organization.activeOrganization.organization_id}`}>{children}</div>}
      </main>
      <Footer />
    </div>
  </RequireAuth>;
}

export function ResourceMessage({ loading, error, retry }: { loading: boolean; error: string | null; retry: () => void }) {
  if (loading) return <p role="status">Loading...</p>;
  if (error) return <div role="alert" className={PANEL}><p>{error}</p><button type="button" onClick={retry} className={`${BTN_GHOST} mt-3`}>Try again</button></div>;
  return null;
}
