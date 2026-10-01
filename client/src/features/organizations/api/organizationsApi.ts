import api from "@shared/api/http";

export type OrganizationMembership = {
  organization_id: string;
  organization_name: string;
  organization_kind: "personal" | "school" | "tutoring" | "corporate";
  role: string;
  status: "active";
  is_active: boolean;
  active_scope_recovered: boolean;
};

export type ActiveOrganization = Omit<
  OrganizationMembership,
  "status" | "is_active" | "active_scope_recovered"
>;

export type OrganizationInvitation = {
  id: string;
  organization_id: string;
  email: string;
  role: "admin" | "author" | "facilitator" | "learner" | "guardian" | "auditor";
  status: "invited" | "accepting" | "accepted" | "declined" | "revoked" | "expired";
  expires_at: string;
  created_at: string;
};

export type OrganizationMember = {
  user_id: string;
  email: string | null;
  username: string | null;
  full_name: string | null;
  role: string;
  status: "active" | "suspended" | "removed";
};

export type OrganizationMemberPage = {
  items: OrganizationMember[];
  next_cursor: string | null;
};

export type OrganizationInvitationPage = {
  items: OrganizationInvitation[];
  next_cursor: string | null;
};

export const organizationsApi = {
  async listMemberships(): Promise<OrganizationMembership[]> {
    const { data } = await api.get<OrganizationMembership[]>("/api/organizations/memberships");
    return data;
  },

  async selectActiveOrganization(organizationId: string): Promise<ActiveOrganization> {
    const { data } = await api.put<ActiveOrganization>("/api/organizations/active", {
      organization_id: organizationId,
    });
    return data;
  },

  async createOrganization(payload: {
    name: string;
    kind: "school" | "tutoring" | "corporate";
  }): Promise<ActiveOrganization> {
    const { data } = await api.post<ActiveOrganization>("/api/organizations", payload);
    return data;
  },

  async listInvitations(cursor?: string): Promise<OrganizationInvitationPage> {
    const { data } = await api.get<OrganizationInvitationPage>("/api/organizations/invitations", {
      params: cursor ? { cursor } : undefined,
    });
    return data;
  },

  async listMembers(cursor?: string): Promise<OrganizationMemberPage> {
    const { data } = await api.get<OrganizationMemberPage>("/api/organizations/members", {
      params: cursor ? { cursor } : undefined,
    });
    return data;
  },

  async updateMemberStatus(
    userId: string,
    status: "active" | "suspended" | "removed",
  ): Promise<void> {
    await api.patch(`/api/organizations/memberships/${userId}`, { status });
  },

  async invite(payload: {
    email: string;
    role: OrganizationInvitation["role"];
    expires_in_days?: number;
  }): Promise<OrganizationInvitation> {
    const { data } = await api.post<OrganizationInvitation>("/api/organizations/invitations", payload);
    return data;
  },

  async revokeInvitation(invitationId: string): Promise<OrganizationInvitation> {
    const { data } = await api.post<OrganizationInvitation>(
      `/api/organizations/invitations/${invitationId}/revoke`,
    );
    return data;
  },

  async acceptInvitation(token: string): Promise<{ organization_id: string }> {
    const { data } = await api.post<{ organization_id: string }>(
      "/api/organizations/invitations/accept",
      { token },
    );
    return data;
  },

  async declineInvitation(token: string): Promise<void> {
    await api.post("/api/organizations/invitations/decline", { token });
  },
};
