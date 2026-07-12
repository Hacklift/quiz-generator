"use client";

import React, { useState } from "react";
import SignInModal from "@features/auth/components/SignInModal";
import { useAuth } from "@features/auth/context/authContext";
import {
  createCheckoutSession,
  getBillingErrorMessage,
} from "@features/profile/api/billingApi";
import { BillingPlanAction, billingPlans } from "@shared/config/billingPlans";

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
      setError(getBillingErrorMessage(err, "Unable to start checkout."));
      setActivePlan(null);
    }
  };

  return (
    <section id="pricing" className="py-12 bg-[#f4f4f4]">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#143E6F]/70">
            Pricing
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-[#102347] sm:text-3xl">
            Pick a plan that fits how you build quizzes
          </h2>
          <p className="mt-3 max-w-2xl mx-auto text-sm text-gray-600 sm:text-base">
            Start free, then upgrade when you want Stripe-powered billing,
            expanded usage, and premium workflow perks.
          </p>
        </div>

        {error ? (
          <div className="max-w-3xl mx-auto mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 md:grid-cols-3">
          {billingPlans.map(
            ({ plan, billingPeriod, price, features, action }, index) => {
              const isCurrentPlan =
                action !== "free" &&
                user?.subscription_plan === action &&
                ["active", "trialing"].includes(
                  user?.subscription_status || "",
                );
              const isBusy = activePlan === action;
              const isFeatured = index > 0;

              return (
                <div
                  key={action}
                  className={`rounded-3xl p-6 text-left flex flex-col shadow-md ${
                    isFeatured
                      ? "bg-white border border-[#143E6F]/10"
                      : "bg-[#fbfbfb] border border-[#d5d9df]"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-xl font-bold text-[#102347]">
                        {plan}
                      </h3>
                      <p className="mt-1 text-sm text-gray-500">
                        {billingPeriod || "Included"}
                      </p>
                    </div>
                    {isCurrentPlan ? (
                      <span className="rounded-full bg-[#143E6F]/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#143E6F]">
                        Current
                      </span>
                    ) : null}
                  </div>

                  <p className="mt-5 text-3xl font-bold text-[#0F2654]">
                    {price}
                  </p>
                  <ul className="mt-6 space-y-3 text-sm text-gray-700 flex-1">
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
                    className="mt-6 w-full bg-[#0F2654] text-white py-3 rounded-2xl hover:bg-[#0C2142] transition disabled:cursor-not-allowed disabled:opacity-60"
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
      </div>

      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={() => {}}
      />
    </section>
  );
}
