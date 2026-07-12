import { api } from "@shared/api/http";

export interface CheckoutSessionResponse {
  checkout_url: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface SubscriptionSummary {
  subscription_plan: string;
  subscription_status: string;
  stripe_customer_id?: string | null;
  stripe_subscription_id?: string | null;
  current_period_end?: string | null;
}

export interface BillingHistoryItem {
  invoice_id: string;
  amount_paid: number;
  currency: string;
  status: string;
  invoice_pdf?: string | null;
  hosted_invoice_url?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  created_at?: string | null;
  description?: string | null;
}

export interface BillingHistoryResponse {
  invoices: BillingHistoryItem[];
}

export const getBillingErrorMessage = (error: any, fallback: string): string =>
  error?.response?.data?.detail || error?.message || fallback;

export const createCheckoutSession = async (
  plan: "monthly" | "yearly",
): Promise<CheckoutSessionResponse> => {
  const response = await api.post("/api/billing/create-checkout-session", {
    plan,
  });
  return response.data as CheckoutSessionResponse;
};

export const getSubscriptionSummary =
  async (): Promise<SubscriptionSummary> => {
    const response = await api.get("/api/billing/subscription");
    return response.data as SubscriptionSummary;
  };

export const createPortalSession = async (): Promise<PortalSessionResponse> => {
  const response = await api.post("/api/billing/create-portal-session");
  return response.data as PortalSessionResponse;
};

export const getBillingHistory = async (): Promise<BillingHistoryResponse> => {
  const response = await api.get("/api/billing/history");
  return response.data as BillingHistoryResponse;
};
