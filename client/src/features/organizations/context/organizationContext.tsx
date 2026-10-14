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
  const [scopeVersion, setScopeVersion] = useState(0);
  const requestVersion = useRef(0);

  useEffect(() => {
    const version = ++requestVersion.current;
    if (authLoading) {
      return;
    }
    if (!isAuthenticated || !user?.id) {
      setMemberships([]);
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
        }
      });
  }, [authLoading, isAuthenticated, user?.id]);

  const activeOrganization = memberships.find((membership) => membership.is_active) ?? null;
  // A browser session can change accounts without remounting _app. Include the
  // account identity so scoped page state cannot survive that transition.
  const scopeKey = `${user?.id ?? "anonymous"}:${scopeVersion}`;

  const switchOrganization = async (organizationId: string) => {
    if (organizationId === activeOrganization?.organization_id) {
      return;
    }
    const selected = await organizationsApi.selectActiveOrganization(organizationId);
    try {
      const nextMemberships = await organizationsApi.listMemberships();
      setMemberships(nextMemberships.map((membership) => ({
        ...membership,
        is_active: membership.organization_id === selected.organization_id,
      })));
    } catch {
      // The server has already proved and selected this scope. Preserve that
      // state locally even if the refresh endpoint is momentarily unavailable.
      setMemberships((current) => {
        const currentSelection = current.map((membership) => ({
          ...membership,
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
    }
    // A new scope must tear down page-level subscriptions and reload scoped data.
    setScopeVersion((current) => current + 1);
  };

  return (
    <OrganizationContext.Provider
      value={{
        memberships,
        activeOrganization,
        isLoading,
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
