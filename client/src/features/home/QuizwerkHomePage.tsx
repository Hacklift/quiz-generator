"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Image from "next/image";
import SignInModal from "@features/auth/components/SignInModal";
import { ROUTES } from "@shared/config/patterns/routes";
import { useAuth } from "@features/auth/context/authContext";
import {
  createCheckoutSession,
  getBillingErrorMessage,
} from "@features/profile/api/billingApi";
import { BillingPlanAction } from "@shared/config/billingPlans";
import {
  PERSONA_CATEGORIES,
  PersonaUserType,
  personaGenerateHref,
} from "@shared/config/persona";
import {
  archivo,
  BTN_GHOST,
  BTN_INVERSE,
  BTN_PRIMARY,
  CONTAINER,
  FeatureRow,
  Kicker,
  Microlabel,
  ResultBar,
} from "@shared/ui/quizwerk";
import HeroMockup from "./HeroMockup";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

/* ── data ────────────────────────────────────────────────────────────── */

/* ── page ────────────────────────────────────────────────────────────── */

export default function QuizwerkHomePage() {
  const { t: uiText } = useTranslation("ui");

  const TESTIMONIALS = [
    {
      quote: uiText("m8bb253bfcd6fb35e"),
      who: uiText("m6f8791b818f35b77"),
    },
    {
      quote: uiText("mc8e91d55d152c8af"),
      who: uiText("m9748b6622ac9b23a"),
    },
    {
      quote: uiText("me937fef69ec1f2c0"),
      who: uiText("ma6e242fc1b815deb"),
    },
  ];

  const PLANS: {
    name: string;
    microlabel?: string;
    price: string;
    unit?: string;
    features: string[];
    cta: string;
    action: BillingPlanAction;
    featured?: boolean;
  }[] = [
    {
      name: "Free",
      price: "$0",
      features: [
        uiText("mb4fd43317d3cebca"),
        uiText("m78d1d628a1c8271d"),
        uiText("m8e9bdef74a35ae63"),
        uiText("mc3ad1eb7820f29a8"),
      ],
      cta: uiText("m22a1d78d60d5d6c4"),
      action: "free",
    },
    {
      name: "Pro",
      microlabel: uiText("m6b174731b398269b"),
      price: "$20",
      unit: uiText("m57cbd84fd6e0495f"),
      features: [
        uiText("m4fe56bc1cfe199a6"),
        uiText("m6f6f78bc78b871f3"),
        uiText("m14bfb5c0b7429833"),
        uiText("m4df8b8619d3ae8f6"),
        uiText("macea4b408437dfa3"),
      ],
      cta: uiText("m12657108fe5682e9"),
      action: "monthly",
      featured: true,
    },
    {
      name: "Premium",
      price: "$100",
      unit: uiText("m47db0b7300016ece"),
      features: [
        uiText("m9a64f5485112d5d4"),
        uiText("mf07e3a78d57210f0"),
        uiText("m59880896bb94a3d5"),
        uiText("mfeb06579056710ee"),
      ],
      cta: uiText("m761ea84045f070da"),
      action: "yearly",
    },
  ];

  const HOW_IT_WORKS = [
    {
      n: "01",
      title: uiText("m1a18623bd55cb315"),
      copy: uiText("m9ac36347c8166c66"),
    },
    {
      n: "02",
      title: uiText("m8450ea3dff069e52"),
      copy: uiText("ma3e1000f0bc688bf"),
    },
    {
      n: "03",
      title: uiText("md7cbe9ec3adb889e"),
      copy: uiText("ma8cc95c85f84b505"),
    },
    {
      n: "04",
      title: uiText("mdab70f7b15cc4d52"),
      copy: uiText("m90f84ded140cce8b"),
    },
  ];

  const STATS = [
    { value: "12s", label: uiText("m43ea1737194c900c") },
    { value: "3", label: uiText("m7940c74b38157434") },
    { value: "50", label: uiText("ma4ebf4f92bbc0c7c") },
    { value: "0", label: uiText("mab23e73cf7d24154") },
  ];

  const { categories, t: personaText } = usePersonaCopy();
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<"monthly" | "yearly" | null>(
    null,
  );
  const [billingError, setBillingError] = useState("");

  const goGenerate = () => router.push("/generate");
  const goJoin = () => router.push("/quiz-access");

  const pickPersona = (userType: PersonaUserType) => {
    router.push(personaGenerateHref(userType));
  };

  const handlePlanSelection = async (action: BillingPlanAction) => {
    setBillingError("");
    if (action === "free") {
      goGenerate();
      return;
    }
    if (isLoading) return;
    if (!isAuthenticated) {
      setIsLoginOpen(true);
      return;
    }
    try {
      setActivePlan(action);
      const { checkout_url } = await createCheckoutSession(action);
      window.location.assign(checkout_url);
    } catch (err: any) {
      setBillingError(getBillingErrorMessage(err, "Unable to start checkout."));
      setActivePlan(null);
    }
  };

  const isCurrentPlan = (action: BillingPlanAction) =>
    action !== "free" &&
    user?.subscription_plan === action &&
    ["active", "trialing"].includes(user?.subscription_status || "");

  return (
    <div className={`${archivo.className} bg-paper text-ink antialiased`}>
      {/* ── 1. Nav ── */}
      <header className="border-b-2 border-divider">
        <nav
          className={`${CONTAINER} flex flex-wrap items-center gap-x-[24px] gap-y-[10px] py-[14px]`}
        >
          <Link
            href="/"
            className="mr-auto text-[18px] font-extrabold tracking-[-0.015em]"
          >
            {uiText("m44523d5233cb56d9")}
          </Link>
          <a
            href="#product"
            className="min-h-[44px] content-center text-[15px] hover:text-brand"
          >
            {uiText("mfb9ef894175c3274")}
          </a>
          <a
            href="#categories"
            className="min-h-[44px] content-center text-[15px] hover:text-brand"
          >
            {uiText("mb8b1d894c6837252")}
          </a>
          <a
            href="#pricing"
            className="min-h-[44px] content-center text-[15px] hover:text-brand"
          >
            {uiText("mdfe95783edfef791")}
          </a>
          <button
            type="button"
            onClick={goJoin}
            className="min-h-[44px] cursor-pointer text-[15px] hover:text-brand"
          >
            {uiText("m91778520c1f39aef")}
          </button>
          <button type="button" onClick={goGenerate} className={BTN_PRIMARY}>
            {uiText("md30398676470782e")}
          </button>
        </nav>
      </header>

      <main>
        {/* ── 2. Hero ── */}
        <section className={`${CONTAINER} py-[clamp(48px,7vw,84px)]`}>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] items-center gap-[clamp(32px,5vw,88px)]">
            <div>
              <h1 className="ml-[-0.058em] text-[clamp(42px,5.4vw,76px)] font-extrabold leading-[1.06] tracking-[-0.02em]">
                {uiText("ma707b9e8a5801925")}
                <br />
                {uiText("mc9eec20bb263332e")}
              </h1>
              <p className="mt-[24px] max-w-[52ch] text-[17px] leading-[28px]">
                {uiText("m930d775dc71bcd87")}
              </p>
              <div className="mt-[32px] flex flex-wrap gap-[14px]">
                <button
                  type="button"
                  onClick={goGenerate}
                  className={BTN_PRIMARY}
                >
                  {uiText("md30398676470782e")}
                </button>
                <button type="button" onClick={goJoin} className={BTN_GHOST}>
                  {uiText("m21e31e177db66d84")}
                </button>
              </div>
            </div>
            <HeroMockup />
          </div>
        </section>

        {/* ── 3. Stat row ── */}
        <section className="border-y-2 border-divider">
          <div
            className={`${CONTAINER} grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-[28px] py-[42px]`}
          >
            {STATS.map((stat) => (
              <div key={stat.label}>
                <p className="text-[clamp(34px,3.4vw,48px)] font-extrabold leading-none tracking-[-0.015em] text-brand [font-variant-numeric:tabular-nums]">
                  {stat.value}
                </p>
                <p className="mt-[10px] text-[13px] uppercase tracking-[0.08em] text-ink/70">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── 4. Categories band — full-bleed navy ── */}
        <section id="categories" className="bg-brand text-paper">
          <div className={`${CONTAINER} py-[84px]`}>
            <Kicker onPaper>{personaText("home.kicker")}</Kicker>
            <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
              {personaText("home.heading")}
            </h2>
            <p className="mt-[12px] max-w-[52ch] text-[15.5px] leading-[28px] text-paper/80">
              {personaText("home.description")}
            </p>
            <div className="mt-[48px] grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-x-[64px] gap-y-[40px]">
              {PERSONA_CATEGORIES.map((key) => {
                const group = categories[key];
                return (
                  <div key={key}>
                    <h3 className="text-[22px] font-extrabold tracking-[-0.015em]">
                      {group.label}
                    </h3>
                    <p className="mb-[20px] mt-[4px] text-[13.5px] text-paper/70">
                      {group.description}
                    </p>
                    {group.userTypes.map((row) => (
                      <button
                        key={row.slug}
                        type="button"
                        onClick={() => pickPersona(row.slug)}
                        className="block w-full cursor-pointer border-t-2 border-paper/30 px-[6px] py-[16px] text-left transition hover:bg-paper/[0.12] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-paper"
                      >
                        <span className="flex items-center gap-[14px]">
                          <span className="h-[8px] w-[8px] flex-none bg-paper" />
                          <span className="flex-1">
                            <span className="block text-[17px] font-extrabold leading-[1.2]">
                              {row.label}
                            </span>
                            <span className="mt-[3px] block text-[13.5px] text-paper/[0.72]">
                              {row.description}
                            </span>
                          </span>
                          <span aria-hidden="true" className="text-[18px]">
                            →
                          </span>
                        </span>
                      </button>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── 5. Features ── */}
        <section id="product" className={`${CONTAINER} pb-[28px] pt-[70px]`}>
          <Kicker>{uiText("m83c19419a72d375f")}</Kicker>
          <FeatureRow
            n="01"
            title={uiText("ma21991194f35cefc")}
            copy="Type the subject — photosynthesis, GDPR, the new expense policy — pick a format and a length, and get a clean draft with the answer key in seconds."
            vignette={
              <div>
                <Microlabel>{uiText("m7e61847d61d65d9e")}</Microlabel>
                <div className="border-2 border-ink px-[12px] py-[10px] text-[14px]">
                  {uiText("m38280bcb1d9d117f")}
                </div>
                <div className="mt-[12px] flex flex-wrap gap-[8px]">
                  <span className="bg-brand-100 px-[10px] py-[3px] text-[11px] tracking-[0.02em] text-brand-800">
                    {uiText("m79fefc32357d38fa")}
                  </span>
                  <span className="border border-brand px-[10px] py-[3px] text-[11px] tracking-[0.02em] text-brand-700">
                    {uiText("m8b241a7be356eef3")}
                  </span>
                </div>
                <div className="mt-[14px]">
                  <span className={BTN_PRIMARY}>
                    {uiText("mf958f95accdab6f3")}
                  </span>
                </div>
              </div>
            }
          />
          <FeatureRow
            n="02"
            title={uiText("m6dd15f4d068f39be")}
            copy="Put a join code on the projector. Participants answer on their own phones, scores tally in real time, and nobody installs anything."
            vignette={
              <div>
                <Microlabel>{uiText("m30b1232c5d22f300")}</Microlabel>
                <p className="text-[52px] font-extrabold leading-none tracking-[0.08em]">
                  {uiText("m18824f326b3f30cb")}
                </p>
                <p className="mt-[14px] flex items-center gap-[8px] text-[13px] text-ink/[0.78]">
                  <span className="h-[8px] w-[8px] animate-live-pulse bg-brand" />
                  {uiText("m9fc0be89888d53bf")}
                </p>
              </div>
            }
          />
          <FeatureRow
            n="03"
            title={uiText("mda2d61e869311f25")}
            copy="Every session lands in your workspace: per-question scores, common misses, and one-click export to PDF or text — for the grade book or the compliance file."
            vignette={
              <div>
                <Microlabel>{uiText("me3097200901173c9")}</Microlabel>
                <ResultBar q="Q1" pct={92} tone="brand" />
                <ResultBar q="Q2" pct={71} tone="brand" />
                <ResultBar q="Q3" pct={38} tone="brand-300" />
              </div>
            }
          />
        </section>

        {/* ── 6. How it works ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <Kicker>{uiText("m9c870aa6e5e93270")}</Kicker>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-[28px]">
            {HOW_IT_WORKS.map((step) => (
              <div key={step.n}>
                <p className="text-[15px] font-extrabold [font-variant-numeric:tabular-nums]">
                  {step.n}
                </p>
                <h3 className="mt-[10px] text-[18px] font-extrabold tracking-[-0.015em]">
                  {step.title}
                </h3>
                <p className="mt-[6px] text-[14px] leading-[24px] text-ink/[0.78]">
                  {step.copy}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── 7. In the room ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] items-center gap-[clamp(32px,5vw,64px)]">
            <div>
              <Kicker>{uiText("mefec5409e54b497d")}</Kicker>
              <h2 className="text-[32px] font-extrabold leading-[1.12] tracking-[-0.015em]">
                {uiText("m58273cb0dbb43bad")}
              </h2>
              <p className="mt-[16px] max-w-[52ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                {uiText("mf475ada2cfe0bf56")}
              </p>
            </div>
            <div className="aspect-[951/665] w-full overflow-hidden border-2 border-divider">
              <Image
                src="/images/hquiz1.png"
                alt={uiText("m35c29bb4d234d676")}
                width={951}
                height={665}
                className="h-full w-full object-cover [filter:grayscale(1)_contrast(1.08)]"
              />
            </div>
          </div>
        </section>

        {/* ── 8. Pricing ── */}
        <section
          id="pricing"
          className={`${CONTAINER} border-t-2 border-divider py-[70px]`}
        >
          <Kicker>{uiText("mdfe95783edfef791")}</Kicker>
          <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
            {uiText("m276e1b83c2c5bee8")}
          </h2>
          {billingError ? (
            <p className="mt-[16px] border-2 border-brand-700 px-[14px] py-[10px] text-[14px] text-brand-700">
              {billingError}
            </p>
          ) : null}
          <div className="mt-[42px] grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-[36px]">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`flex flex-col border-t-2 pt-[20px] ${
                  plan.featured ? "border-brand" : "border-divider"
                }`}
              >
                {plan.microlabel ? (
                  <p className="mb-[6px] text-[11px] font-extrabold uppercase tracking-[0.1em] text-brand-700">
                    {plan.microlabel}
                  </p>
                ) : null}
                <h3 className="text-[20px] font-extrabold tracking-[-0.015em]">
                  {plan.name}
                </h3>
                <p className="mt-[10px] text-[44px] font-extrabold leading-none tracking-[-0.015em] [font-variant-numeric:tabular-nums]">
                  {plan.price}
                  {plan.unit ? (
                    <span className="ml-[6px] text-[15px] font-normal tracking-normal text-ink/70">
                      {plan.unit}
                    </span>
                  ) : null}
                </p>
                <ul className="mb-[28px] mt-[22px] flex-1 space-y-[12px]">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-center gap-[12px] text-[15px]"
                    >
                      <span className="h-[8px] w-[8px] flex-none bg-brand" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <div>
                  <button
                    type="button"
                    onClick={() => handlePlanSelection(plan.action)}
                    disabled={
                      activePlan === plan.action || isCurrentPlan(plan.action)
                    }
                    className={`${plan.featured ? BTN_PRIMARY : BTN_GHOST} disabled:cursor-not-allowed disabled:opacity-60`}
                  >
                    {isCurrentPlan(plan.action)
                      ? uiText("m37ca715f53b6bb83")
                      : activePlan === plan.action
                        ? uiText("m0d83b98bebfb5add")
                        : plan.cta}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── 9. Testimonials ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <Kicker>{uiText("m9b926536b47326f7")}</Kicker>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[36px]">
            {TESTIMONIALS.map((t) => (
              <figure
                key={t.who}
                className="border-t-2 border-divider pt-[20px]"
              >
                <blockquote className="text-[19px] font-extrabold leading-[27px] tracking-[-0.015em]">
                  {t.quote}
                </blockquote>
                <figcaption className="mt-[14px] text-[13px] uppercase tracking-[0.08em] text-ink/70">
                  {t.who}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        {/* ── 10. Poster close — full-bleed navy ── */}
        <section className="bg-brand text-paper">
          <div className={`${CONTAINER} py-[84px]`}>
            <h3 className="max-w-[18ch] text-[clamp(34px,4.2vw,56px)] font-extrabold leading-[1.06] tracking-[-0.02em]">
              {uiText("mfd9ffd24207032f6")}
            </h3>
            <button
              type="button"
              onClick={goGenerate}
              className={`${BTN_INVERSE} mt-[32px]`}
            >
              {uiText("mff9c5dc6f20dbe0a")}
            </button>
          </div>
        </section>
      </main>

      {/* ── 11. Footer ── */}
      <footer
        className={`${CONTAINER} flex flex-wrap items-center justify-between gap-x-[28px] gap-y-[12px] py-[28px] text-[13px] text-ink/70`}
      >
        <span className="text-[15px] font-extrabold tracking-[-0.015em] text-ink">
          {uiText("m44523d5233cb56d9")}
        </span>
        <span className="flex flex-wrap gap-x-[24px] gap-y-[8px]">
          <a
            href="#product"
            className="min-h-[44px] content-center hover:text-brand"
          >
            {uiText("mfb9ef894175c3274")}
          </a>
          <a
            href="#categories"
            className="min-h-[44px] content-center hover:text-brand"
          >
            {uiText("mb8b1d894c6837252")}
          </a>
          <a
            href="#pricing"
            className="min-h-[44px] content-center hover:text-brand"
          >
            {uiText("mdfe95783edfef791")}
          </a>
          <button
            type="button"
            onClick={goJoin}
            className="min-h-[44px] cursor-pointer hover:text-brand"
          >
            {uiText("m21e31e177db66d84")}
          </button>
        </span>
        <span>{uiText("meaddd10c00679ccd")}</span>
      </footer>

      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        redirectTo={ROUTES.DASHBOARD}
        switchToSignUp={() => {}}
      />
    </div>
  );
}
