"use client";
import { useTranslation } from "react-i18next";

import { useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import {
  BillingHistoryItem,
  getBillingErrorMessage,
  getBillingHistory,
} from "@features/profile/api/billingApi";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";

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
  const { t: uiText } = useTranslation("ui");

  const [invoices, setInvoices] = useState<BillingHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadBillingHistory = async () => {
      try {
        const response = await getBillingHistory();
        setInvoices(response.invoices || []);
      } catch (error: any) {
        toast.error(
          getBillingErrorMessage(error, "Unable to load billing history."),
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadBillingHistory();
  }, []);

  return (
    <RequireAuth
      title={uiText("m1a18cccbe11fe65b")}
      description={uiText("md6bcfb2d2d8637bf")}
    >
      <div className="min-h-screen bg-[#f7f7f5] text-[#102347]">
        <NavBar />
        <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
          <div className="flex items-center justify-between gap-4 mb-8">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-[#143E6F]/70">
                {uiText("m3ac8bbca9a74cfbd")}
              </p>
              <h1 className="text-3xl sm:text-4xl font-bold mt-2">
                {uiText("m5ade08611d1f4322")}
              </h1>
              <p className="mt-3 text-gray-600 max-w-2xl">
                {uiText("m22de0f29f74f32ee")}
              </p>
            </div>
            <Link
              href="/profile"
              className="rounded-lg border border-[#143E6F]/20 px-4 py-2 text-sm font-medium text-[#143E6F] hover:bg-[#143E6F]/5"
            >
              {uiText("m351f14c7716123b8")}
            </Link>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-[#143E6F]/10 overflow-hidden">
            {isLoading ? (
              <div className="px-6 py-16 text-center text-gray-500">
                {uiText("m6048993fb74846e4")}
              </div>
            ) : invoices.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <p className="text-lg font-semibold text-[#102347]">
                  {uiText("m92d2d0ce0bd393f4")}
                </p>
                <p className="mt-2 text-gray-600">
                  {uiText("mee8eab0374fa4a83")}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-[#f8fafc]">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("m99c40ab405926cb5")}
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("m526e0087cc3f254d")}
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("m6e795d4d3cc21c5c")}
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("m49e96d7cdf58069c")}
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("m920e413c7d411b61")}
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {uiText("mdad5a969231390f5")}
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
                          {invoice.description || uiText("m52199592a197757b")}
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
                              {uiText("m3600894333963a24")}
                            </a>
                          ) : (
                            <span className="text-gray-400">
                              {uiText("mca184496974204a0")}
                            </span>
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
