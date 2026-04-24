"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";
import RequireAuth from "../components/auth/RequireAuth";
import { getBillingHistory, BillingHistoryItem } from "../lib";

const formatMoney = (amount: number, currency: string) => {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
    }).format(amount);
  } catch {
    return `${currency || "USD"} ${amount.toFixed(2)}`;
  }
};

const formatDate = (value?: string | null) => {
  if (!value) {
    return "N/A";
  }
  return new Date(value).toLocaleDateString();
};

const formatStatus = (status?: string) => {
  if (!status) {
    return "Unknown";
  }
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

export default function BillingHistoryPage() {
  const [invoices, setInvoices] = useState<BillingHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadBillingHistory = async () => {
      try {
        const response = await getBillingHistory();
        setInvoices(response.invoices || []);
      } catch (error: any) {
        toast.error(
          error?.response?.data?.detail ||
            error?.message ||
            "Unable to load billing history.",
        );
      } finally {
        setIsLoading(false);
      }
    };

    loadBillingHistory();
  }, []);

  return (
    <RequireAuth
      title="Sign in to view billing history"
      description="You need an account to review Stripe invoices and payment records."
    >
      <div className="min-h-screen bg-[#f7f7f5] text-[#102347]">
        <NavBar />
        <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center justify-between gap-4 mb-8">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-[#143E6F]/70">
                Billing
              </p>
              <h1 className="text-3xl sm:text-4xl font-bold mt-2">
                Billing History
              </h1>
              <p className="mt-3 text-gray-600 max-w-2xl">
                Review invoices, payment status, and downloadable receipts for
                your Stripe subscription charges.
              </p>
            </div>
            <Link
              href="/profile"
              className="rounded-lg border border-[#143E6F]/20 px-4 py-2 text-sm font-medium text-[#143E6F] hover:bg-[#143E6F]/5"
            >
              Back to Profile
            </Link>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-[#143E6F]/10 overflow-hidden">
            {isLoading ? (
              <div className="px-6 py-16 text-center text-gray-500">
                Loading billing history...
              </div>
            ) : invoices.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <p className="text-lg font-semibold text-[#102347]">
                  No invoices yet
                </p>
                <p className="mt-2 text-gray-600">
                  Stripe billing records will appear here after the first paid
                  subscription charge is created.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-[#f8fafc]">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Date
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Description
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Period
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Amount
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Status
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Receipt
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {invoices.map((invoice) => (
                      <tr key={invoice.invoice_id} className="align-top">
                        <td className="px-6 py-4 text-sm text-gray-700 whitespace-nowrap">
                          {formatDate(invoice.created_at)}
                        </td>
                        <td className="px-6 py-4 text-sm text-[#102347]">
                          {invoice.description || "Subscription payment"}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700 whitespace-nowrap">
                          {formatDate(invoice.period_start)} -{" "}
                          {formatDate(invoice.period_end)}
                        </td>
                        <td className="px-6 py-4 text-sm font-semibold text-[#102347] whitespace-nowrap">
                          {formatMoney(invoice.amount_paid, invoice.currency)}
                        </td>
                        <td className="px-6 py-4 text-sm whitespace-nowrap">
                          <span className="inline-flex rounded-full bg-[#143E6F]/10 px-3 py-1 font-medium text-[#143E6F]">
                            {formatStatus(invoice.status)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm whitespace-nowrap">
                          {invoice.invoice_pdf || invoice.hosted_invoice_url ? (
                            <a
                              href={
                                invoice.invoice_pdf ||
                                invoice.hosted_invoice_url ||
                                "#"
                              }
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#143E6F] font-medium hover:underline"
                            >
                              View Invoice
                            </a>
                          ) : (
                            <span className="text-gray-400">Unavailable</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
