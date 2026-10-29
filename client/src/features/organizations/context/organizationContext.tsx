import {
  createContext,
  Fragment,
  ReactNode,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import toast from "react-hot-toast";
import { useAuth } from "@features/auth/context/authContext";
import {
  organizationsApi,
  type OrganizationMembership,
} from "@features/organizations/api/organizationsApi";

type OrganizationContextValue = {
  memberships: OrganizationMembership[];
  activeOrganization: OrganizationMembership | null;
  isLoading: boolean;
  scopeVersion: number;
  scopeKey: string;
  switchOrganization: (organizationId: string) => Promise<void>;
};

const OrganizationContext = createContext<OrganizationContextValue | undefined>(undefined);

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [resolvedUserId, setResolvedUserId] = useState<string | null>(null);
  const [scopeVersion, setScopeVersion] = useState(0);
  const requestVersion = useRef(0);
  const currentUserId = useRef(user?.id);
  const switchInFlight = useRef(false);
  currentUserId.current = user?.id;

  useEffect(() => {
    const version = ++requestVersion.current;
    if (authLoading) {
      return;
    }
    if (!isAuthenticated || !user?.id) {
      setMemberships([]);
      setResolvedUserId(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    void organizationsApi
      .listMemberships()
      .then((nextMemberships) => {
        if (requestVersion.current === version) {
          setMemberships(nextMemberships);
          if (nextMemberships.some((membership) => membership.active_scope_recovered)) {
            toast("Your previous workspace is no longer available. Switched to your default workspace.");
          }
        }
      })
      .catch(() => {
        if (requestVersion.current === version) {
          setMemberships([]);
          toast.error("Unable to load your organizations.");
        }
      })
      .finally(() => {
        if (requestVersion.current === version) {
          setIsLoading(false);
          setResolvedUserId(user.id);
        }
      });
    return () => { requestVersion.current += 1; };
  }, [authLoading, isAuthenticated, user?.id]);

  const activeOrganization = memberships.find((membership) => membership.is_active) ?? null;
  // Account transitions must not authorize UI from the previous identity's
  // memberships while the next server-backed membership lookup is pending.
  const scopeLoading = authLoading || isLoading || Boolean(
    isAuthenticated && user?.id && resolvedUserId !== user.id,
  );
  // A browser session can change accounts without remounting _app. Include the
  // account identity so scoped page state cannot survive that transition.
  const scopeKey = `${user?.id ?? "anonymous"}:${scopeVersion}`;

  const switchOrganization = async (organizationId: string) => {
    if (organizationId === activeOrganization?.organization_id) {
      return;
    }
    if (!isAuthenticated || !user?.id || switchInFlight.current) {
      throw new Error("A workspace change cannot be started right now.");
    }
    const userId = user.id;
    const version = ++requestVersion.current;
    const isCurrent = () => currentUserId.current === userId && requestVersion.current === version;
    const assertCurrent = () => {
      if (!isCurrent()) throw new Error("The account changed during the workspace switch.");
    };
    switchInFlight.current = true;
    setIsLoading(true);
    try {
      const selected = await organizationsApi.selectActiveOrganization(organizationId);
      assertCurrent();
      // Switch page scope immediately after the server commits, rather than
      // leaving old forms mounted during the optional membership refresh.
      setMemberships((current) => {
        const currentSelection = current.map((membership) => ({
          ...membership,
          ...(membership.organization_id === selected.organization_id ? selected : {}),
          is_active: membership.organization_id === selected.organization_id,
        }));
        return currentSelection.some((membership) => membership.is_active)
          ? currentSelection
          : [...currentSelection, {
              ...selected,
              status: "active",
              is_active: true,
              active_scope_recovered: false,
            }];
      });
      setScopeVersion((current) => current + 1);
      try {
        const nextMemberships = await organizationsApi.listMemberships();
        assertCurrent();
        setMemberships(nextMemberships.map((membership) => ({
          ...membership,
          is_active: membership.organization_id === selected.organization_id,
        })));
      } catch (error) {
        // A failed refresh never rolls back an already proven selection.
        if (!isCurrent()) throw error;
      }
    } finally {
      switchInFlight.current = false;
      if (isCurrent()) {
        setResolvedUserId(userId);
        setIsLoading(false);
      }
    }
  };

  return (
    <OrganizationContext.Provider
      value={{
        memberships,
        activeOrganization,
        isLoading: scopeLoading,
        scopeVersion,
        scopeKey,
        switchOrganization,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error("useOrganization must be used within OrganizationProvider");
  }
  return context;
}

export function OrganizationScopeBoundary({ children }: { children: ReactNode }) {
  const { scopeKey } = useOrganization();
  return <Fragment key={scopeKey}>{children}</Fragment>;
}
