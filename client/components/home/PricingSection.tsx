"use client";

import React, { useState } from "react";

import SignInModal from "../auth/SignInModal";
import { useAuth } from "../../contexts/authContext";
import { createCheckoutSession } from "../../lib";
import {
  billingPlans,
  BillingPlanAction,
} from "../../lib/constants/billingPlans";

export default function PricingSection() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<"monthly" | "yearly" | null>(
    null,
  );
  const [error, setError] = useState("");

  const handlePlanSelection = async (action: BillingPlanAction) => {
    setError("");

    if (action === "free") {
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
    <section id="pricing" className="py-12 bg-[#f4f4f4]">
      <h2 className="text-2xl font-semibold mb-8 text-center">Pricing</h2>
      {error ? (
        <div className="max-w-3xl mx-auto mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
        {billingPlans.map(
          ({ plan, billingPeriod, price, features, action }, i) => {
            const isCurrentPlan =
              action !== "free" && user?.subscription_plan === action;
            const isBusy = activePlan === action;

            return (
              <div
                key={i}
                className="bg-white rounded shadow-md p-6 text-left flex flex-col"
              >
                <h3 className="text-xl font-bold mb-2">
                  {plan}
                  {billingPeriod ? (
                    <span className="block text-sm font-medium text-gray-500">
                      {billingPeriod}
                    </span>
                  ) : null}
                </h3>
                <p className="text-[#0F2654] font-semibold mb-4">{price}</p>
                <ul className="text-sm text-gray-700 list-disc list-inside mb-6 flex-1">
                  {features.map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={() => handlePlanSelection(action)}
                  disabled={isBusy || isCurrentPlan}
                  className="w-full bg-[#0F2654] text-white py-3 rounded-2xl hover:bg-[#0C2142] transition disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {action === "free"
                    ? "Included"
                    : isCurrentPlan
                      ? "Current Plan"
                      : isBusy
                        ? "Redirecting..."
                        : "Get Started"}
                </button>
              </div>
            );
          },
        )}
      </div>
      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={() => {}}
      />
    </section>
  );
}
