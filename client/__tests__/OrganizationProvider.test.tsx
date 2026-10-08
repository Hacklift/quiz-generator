import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  OrganizationProvider,
  OrganizationScopeBoundary,
  useOrganization,
} from "@features/organizations/context/organizationContext";

const mockListMemberships = jest.fn();
const mockSelectActiveOrganization = jest.fn();
let authState = {
  isAuthenticated: true,
  isLoading: false,
  user: { id: "user-1" },
};

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => authState,
}));

jest.mock("@features/organizations/api/organizationsApi", () => ({
  organizationsApi: {
    listMemberships: () => mockListMemberships(),
    selectActiveOrganization: (organizationId: string) =>
      mockSelectActiveOrganization(organizationId),
  },
}));

function OrganizationProbe() {
  const { activeOrganization, switchOrganization } = useOrganization();
  return (
    <>
      <p data-testid="active-organization">
        {activeOrganization?.organization_id ?? "none"}
      </p>
      <button type="button" onClick={() => void switchOrganization("org-2")}>
        Switch
      </button>
    </>
  );
}

let scopedMounts = 0;

function ScopedProbe() {
  const [mount] = React.useState(() => ++scopedMounts);
  return <p data-testid="scoped-probe">{mount}</p>;
}

describe("OrganizationProvider", () => {
  beforeEach(() => {
    mockListMemberships.mockReset();
    mockSelectActiveOrganization.mockReset();
    authState = {
      isAuthenticated: true,
      isLoading: false,
      user: { id: "user-1" },
    };
    scopedMounts = 0;
    mockListMemberships
      .mockResolvedValueOnce([
        { organization_id: "org-1", organization_name: "Personal", organization_kind: "personal", role: "owner", status: "active", is_active: true },
        { organization_id: "org-2", organization_name: "Acme", organization_kind: "corporate", role: "admin", status: "active", is_active: false },
      ])
      .mockResolvedValueOnce([
        { organization_id: "org-1", organization_name: "Personal", organization_kind: "personal", role: "owner", status: "active", is_active: false },
        { organization_id: "org-2", organization_name: "Acme", organization_kind: "corporate", role: "admin", status: "active", is_active: true },
      ]);
    mockSelectActiveOrganization.mockResolvedValue({
      organization_id: "org-2",
      organization_name: "Acme",
      organization_kind: "corporate",
      role: "admin",
    });
  });

  test("re-proves the selected organization through the server before changing client scope", async () => {
    render(
      <OrganizationProvider>
        <OrganizationProbe />
        <OrganizationScopeBoundary><ScopedProbe /></OrganizationScopeBoundary>
      </OrganizationProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("active-organization")).toHaveTextContent("org-1"));
    fireEvent.click(screen.getByRole("button", { name: "Switch" }));

    await waitFor(() => expect(mockSelectActiveOrganization).toHaveBeenCalledWith("org-2"));
    await waitFor(() => expect(screen.getByTestId("active-organization")).toHaveTextContent("org-2"));
    expect(mockListMemberships).toHaveBeenCalledTimes(2);
  });

  test("remounts scoped content when the authenticated account changes", async () => {
    const view = render(
      <OrganizationProvider>
        <OrganizationScopeBoundary><ScopedProbe /></OrganizationScopeBoundary>
      </OrganizationProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("scoped-probe")).toHaveTextContent("1"));
    authState = {
      isAuthenticated: true,
      isLoading: false,
      user: { id: "user-2" },
    };
    view.rerender(
      <OrganizationProvider>
        <OrganizationScopeBoundary><ScopedProbe /></OrganizationScopeBoundary>
      </OrganizationProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("scoped-probe")).toHaveTextContent("2"));
  });
});
