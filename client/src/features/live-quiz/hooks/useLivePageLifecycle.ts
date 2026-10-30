import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { useAuth } from "@features/auth/context/authContext";
import { useOrganization } from "@features/organizations/context/organizationContext";

export type LivePageGuard = () => boolean;

/** Public sessions stay usable without membership; private access is server-proven. */
export function useLivePageLifecycle(sessionId: string) {
  const router = useRouter();
  const auth = useAuth();
  const organization = useOrganization();
  const scope =
    `${sessionId}:${auth.user?.id ?? "guest"}:${auth.isAuthenticated}:` +
    `${organization.scopeKey}:` +
    `${organization.activeOrganization?.organization_id ?? "none"}`;
  const ready = !auth.isLoading && !organization.isLoading;
  const current = useRef({ scope, ready });
  current.current = { scope, ready };
  const mounted = useRef(true);
  const epoch = useRef(0);
  const destination = useRef<string | null>(null);
  const [isLeaving, setIsLeaving] = useState(false);
  const [recoveryVersion, setRecoveryVersion] = useState(0);

  const capture = useCallback((): LivePageGuard => {
    const startedScope = current.current.scope;
    const startedEpoch = epoch.current;
    return () =>
      mounted.current &&
      current.current.ready &&
      current.current.scope === startedScope &&
      epoch.current === startedEpoch &&
      destination.current === null;
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      epoch.current += 1;
    };
  }, []);

  useEffect(() => {
    const start = (url: string) => {
      destination.current = url;
      epoch.current += 1;
      setIsLeaving(true);
    };
    const failed = (_error: unknown, url: string) => {
      if (destination.current !== url) return;
      destination.current = null;
      setIsLeaving(false);
      // Remount after cancelled navigation: old busy refs and callbacks must
      // not survive into a recovered session screen.
      setRecoveryVersion((version) => version + 1);
    };
    const completed = (url: string) => {
      if (destination.current !== url) return;
      destination.current = null;
      setIsLeaving(false);
      setRecoveryVersion((version) => version + 1);
    };
    router.events.on("routeChangeStart", start);
    router.events.on("routeChangeError", failed);
    router.events.on("routeChangeComplete", completed);
    return () => {
      router.events.off("routeChangeStart", start);
      router.events.off("routeChangeError", failed);
      router.events.off("routeChangeComplete", completed);
    };
  }, [router.events]);

  return {
    ready,
    pageKey: `${scope}:${recoveryVersion}`,
    capture,
    isLeaving,
    isAuthenticated: auth.isAuthenticated,
  };
}

export type LivePageLifecycle = ReturnType<typeof useLivePageLifecycle>;
