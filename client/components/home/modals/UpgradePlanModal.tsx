"use client";

import { Dialog } from "@headlessui/react";
import { X } from "lucide-react";
import { useState } from "react";
import SignInModal from "../../auth/SignInModal";
import { useAuth } from "../../../contexts/authContext";
import { createCheckoutSession } from "../../../lib";
import {
  billingComparisonRows,
  billingPlans,
  BillingPlanAction,
} from "../../../lib/constants/billingPlans";

interface UpgradePlanModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UpgradePlanModal({
  isOpen,
  onClose,
}: UpgradePlanModalProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<"monthly" | "yearly" | null>(
    null,
  );
  const [error, setError] = useState("");

  const handlePlanSelection = async (action: BillingPlanAction) => {
    setError("");

    if (action === "free") {
      onClose();
      return;
    }

    if (isLoading) {
      return;
    }

    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }

    try {
      setActivePlan(action);
      const { checkout_url } = await createCheckoutSession(action);
      onClose();
      window.location.assign(checkout_url);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to start checkout.",
      );
      setActivePlan(null);
    }
  };

  return (
    <>
      <Dialog open={isOpen} onClose={onClose} className="relative z-[120]">
        <div
          className="fixed inset-0 bg-[#0b1730]/55 backdrop-blur-sm"
          aria-hidden="true"
        />
        <div className="fixed inset-0 overflow-y-auto p-4">
          <div className="flex min-h-full items-center justify-center">
            <Dialog.Panel className="w-full max-w-6xl rounded-[28px] bg-[#f7f5ef] shadow-2xl border border-[#143E6F]/10 overflow-hidden">
              <div className="border-b border-[#143E6F]/10 bg-[linear-gradient(135deg,#143E6F_0%,#1f4f87_55%,#f1efe8_55%,#f1efe8_100%)] px-6 py-6 sm:px-8">
                <div className="flex items-start justify-between gap-4">
                  <div className="max-w-2xl">
                    <Dialog.Title className="text-2xl sm:text-3xl font-bold text-white">
                      Choose the right plan
                    </Dialog.Title>
                    <p className="mt-3 text-sm sm:text-base text-white/85">
                      Compare Free, Pro, and Premium in one place, then start
                      checkout directly from this modal.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-full bg-white/90 p-2 text-[#143E6F] hover:bg-white"
                    aria-label="Close upgrade modal"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              <div className="p-6 sm:p-8">
                {error ? (
                  <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                  </div>
                ) : null}

                <div className="grid gap-5 lg:grid-cols-3">
                  {billingPlans.map(
                    ({ plan, billingPeriod, price, features, action }) => {
                      const isCurrentPlan =
                        action !== "free" && user?.subscription_plan === action;
                      const isBusy = activePlan === action;
                      const isHighlighted = action !== "free";

                      return (
                        <div
                          key={action}
                          className={`rounded-3xl border p-6 flex flex-col ${
                            isHighlighted
                              ? "border-[#143E6F]/15 bg-white shadow-md"
                              : "border-[#d7d2c6] bg-[#fbf9f3]"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <h3 className="text-2xl font-bold text-[#102347]">
                                {plan}
                              </h3>
                              {billingPeriod ? (
                                <p className="mt-1 text-sm uppercase tracking-[0.15em] text-[#143E6F]/70">
                                  {billingPeriod}
                                </p>
                              ) : (
                                <p className="mt-1 text-sm uppercase tracking-[0.15em] text-[#6b7280]">
                                  Included
                                </p>
                              )}
                            </div>
                            {isCurrentPlan ? (
                              <span className="rounded-full bg-[#143E6F]/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#143E6F]">
                                Current
                              </span>
                            ) : null}
                          </div>

                          <p className="mt-5 text-4xl font-bold text-[#143E6F]">
                            {price}
                          </p>

                          <ul className="mt-6 space-y-3 text-sm text-[#374151] flex-1">
                            {features.map((feature) => (
                              <li key={feature} className="flex gap-3">
                                <span className="mt-0.5 text-[#143E6F]">•</span>
                                <span>{feature}</span>
                              </li>
                            ))}
                          </ul>

                          <button
                            type="button"
                            onClick={() => handlePlanSelection(action)}
                            disabled={isBusy || isCurrentPlan}
                            className={`mt-6 rounded-2xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
                              action === "free"
                                ? "border border-[#143E6F]/20 bg-white text-[#143E6F] hover:bg-[#143E6F]/5"
                                : "bg-[#143E6F] text-white hover:bg-[#0f2f57]"
                            }`}
                          >
                            {action === "free"
                              ? "Stay on Free"
                              : isCurrentPlan
                                ? "Current Plan"
                                : isBusy
                                  ? "Redirecting..."
                                  : "Subscribe"}
                          </button>
                        </div>
                      );
                    },
                  )}
                </div>

                <div className="mt-8 rounded-3xl border border-[#143E6F]/10 bg-white overflow-hidden">
                  <div className="border-b border-[#143E6F]/10 px-5 py-4">
                    <h4 className="text-lg font-semibold text-[#102347]">
                      Compare plans
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead className="bg-[#f8fafc]">
                        <tr>
                          <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Feature
                          </th>
                          <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Free
                          </th>
                          <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Pro
                          </th>
                          <th className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Premium
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {billingComparisonRows.map((row) => (
                          <tr key={row.label}>
                            <td className="px-5 py-4 text-sm font-medium text-[#102347]">
                              {row.label}
                            </td>
                            <td className="px-5 py-4 text-sm text-gray-600">
                              {row.free}
                            </td>
                            <td className="px-5 py-4 text-sm text-gray-600">
                              {row.monthly}
                            </td>
                            <td className="px-5 py-4 text-sm text-gray-600">
                              {row.yearly}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </Dialog.Panel>
          </div>
        </div>
      </Dialog>

      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={() => {}}
      />
    </>
  );
}
