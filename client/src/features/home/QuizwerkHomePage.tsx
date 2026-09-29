"use client";

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
  PERSONA_TAXONOMY,
  PersonaCategory,
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

/* ── data ────────────────────────────────────────────────────────────── */

const STATS = [
  { value: "12s", label: "Topic to finished draft" },
  { value: "3", label: "Question formats" },
  { value: "50", label: "Questions per quiz, max" },
  { value: "0", label: "Hours spent formatting" },
];

const HOW_IT_WORKS = [
  { n: "01", title: "Enter your topic", copy: "Anything you would train on. One line is enough." },
  { n: "02", title: "Pick the format", copy: "Multiple choice, true–false or short answer. 5 to 50 questions." },
  { n: "03", title: "Review the draft", copy: "Answer keys included. Edit, reorder, regenerate." },
  { n: "04", title: "Run it or ship it", copy: "Live with a join code, or exported to PDF and text." },
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
    features: ["5 quizzes a month", "Basic question types", "Save and share quizzes", "Community templates"],
    cta: "Start free",
    action: "free",
  },
  {
    name: "Pro",
    microlabel: "Most teams",
    price: "$20",
    unit: "/ month",
    features: ["Unlimited quiz generation", "Advanced question types", "Edit and customise questions", "Export to PDF and text", "Priority support"],
    cta: "Get Pro",
    action: "monthly",
    featured: true,
  },
  {
    name: "Premium",
    price: "$100",
    unit: "/ year",
    features: ["Everything in Pro", "Early access to new features", "Personalised templates", "Premium support"],
    cta: "Go Premium",
    action: "yearly",
  },
];

const TESTIMONIALS = [
  {
    quote: "“We ran a 40-person compliance refresher off a join code on the projector. Scoring that used to take an evening happened before the room emptied.”",
    who: "Dana M. — Compliance trainer, logistics",
  },
  {
    quote: "“Topic to printed handout inside the coffee break. My slide decks stopped being the bottleneck.”",
    who: "R. Okafor — L&D lead, fintech",
  },
  {
    quote: "“My Friday revision quiz takes five minutes to set, and the class marks itself before the bell.”",
    who: "T. Adeyemi — Secondary school teacher",
  },
];

/* ── page ────────────────────────────────────────────────────────────── */

export default function QuizwerkHomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<"monthly" | "yearly" | null>(null);
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
        <nav className={`${CONTAINER} flex flex-wrap items-center gap-x-[24px] gap-y-[10px] py-[14px]`}>
          <Link href="/" className="mr-auto text-[18px] font-extrabold tracking-[-0.015em]">
            Quizwerk
          </Link>
          <a href="#product" className="min-h-[44px] content-center text-[15px] hover:text-brand">Product</a>
          <a href="#categories" className="min-h-[44px] content-center text-[15px] hover:text-brand">Categories</a>
          <a href="#pricing" className="min-h-[44px] content-center text-[15px] hover:text-brand">Pricing</a>
          <button type="button" onClick={goJoin} className="min-h-[44px] cursor-pointer text-[15px] hover:text-brand">
            Join a quiz
          </button>
          <button type="button" onClick={goGenerate} className={BTN_PRIMARY}>
            Generate a quiz
          </button>
        </nav>
      </header>

      <main>
        {/* ── 2. Hero ── */}
        <section className={`${CONTAINER} py-[clamp(48px,7vw,84px)]`}>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] items-center gap-[clamp(32px,5vw,88px)]">
            <div>
              <h1 className="ml-[-0.058em] text-[clamp(42px,5.4vw,76px)] font-extrabold leading-[1.06] tracking-[-0.02em]">
                Type a topic.
                <br />
                Run the quiz.
              </h1>
              <p className="mt-[24px] max-w-[52ch] text-[17px] leading-[28px]">
                Quizwerk turns any topic into a ready-to-run quiz — question
                types you choose, answer keys included, delivered live or
                exported to PDF. For the classroom and the training room alike.
              </p>
              <div className="mt-[32px] flex flex-wrap gap-[14px]">
                <button type="button" onClick={goGenerate} className={BTN_PRIMARY}>
                  Generate a quiz
                </button>
                <button type="button" onClick={goJoin} className={BTN_GHOST}>
                  Join a live quiz
                </button>
              </div>
            </div>
            <HeroMockup />
          </div>
        </section>

        {/* ── 3. Stat row ── */}
        <section className="border-y-2 border-divider">
          <div className={`${CONTAINER} grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-[28px] py-[42px]`}>
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
            <Kicker onPaper>Who it&apos;s for</Kicker>
            <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
              Pick the seat you&apos;re sitting in
            </h2>
            <p className="mt-[12px] max-w-[52ch] text-[15.5px] leading-[28px] text-paper/80">
              Two worlds, one generator. Choose a persona and we start you with
              a quiz that fits it — change anything before you run it.
            </p>
            <div className="mt-[48px] grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-x-[64px] gap-y-[40px]">
              {(Object.keys(PERSONA_TAXONOMY) as PersonaCategory[]).map((key) => {
                const group = PERSONA_TAXONOMY[key];
                return (
                  <div key={key}>
                    <h3 className="text-[22px] font-extrabold tracking-[-0.015em]">{group.label}</h3>
                    <p className="mb-[20px] mt-[4px] text-[13.5px] text-paper/70">{group.description}</p>
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
                            <span className="block text-[17px] font-extrabold leading-[1.2]">{row.label}</span>
                            <span className="mt-[3px] block text-[13.5px] text-paper/[0.72]">{row.description}</span>
                          </span>
                          <span aria-hidden="true" className="text-[18px]">→</span>
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
          <Kicker>What Quizwerk does</Kicker>
          <FeatureRow
            n="01"
            title="Generate from a topic"
            copy="Type the subject — photosynthesis, GDPR, the new expense policy — pick a format and a length, and get a clean draft with the answer key in seconds."
            vignette={
              <div>
                <Microlabel>Topic</Microlabel>
                <div className="border-2 border-ink px-[12px] py-[10px] text-[14px]">
                  Fire safety in the workplace
                </div>
                <div className="mt-[12px] flex flex-wrap gap-[8px]">
                  <span className="bg-brand-100 px-[10px] py-[3px] text-[11px] tracking-[0.02em] text-brand-800">
                    Multiple choice
                  </span>
                  <span className="border border-brand px-[10px] py-[3px] text-[11px] tracking-[0.02em] text-brand-700">
                    5 questions
                  </span>
                </div>
                <div className="mt-[14px]">
                  <span className={BTN_PRIMARY}>Generate quiz</span>
                </div>
              </div>
            }
          />
          <FeatureRow
            n="02"
            title="Run it live"
            copy="Put a join code on the projector. Participants answer on their own phones, scores tally in real time, and nobody installs anything."
            vignette={
              <div>
                <Microlabel>Session code</Microlabel>
                <p className="text-[52px] font-extrabold leading-none tracking-[0.08em]">4F7–KQ2</p>
                <p className="mt-[14px] flex items-center gap-[8px] text-[13px] text-ink/[0.78]">
                  <span className="h-[8px] w-[8px] animate-live-pulse bg-brand" />
                  24 participants joined
                </p>
              </div>
            }
          />
          <FeatureRow
            n="03"
            title="Results, kept"
            copy="Every session lands in your workspace: per-question scores, common misses, and one-click export to PDF or text — for the grade book or the compliance file."
            vignette={
              <div>
                <Microlabel>Correct answers by question</Microlabel>
                <ResultBar q="Q1" pct={92} tone="brand" />
                <ResultBar q="Q2" pct={71} tone="brand" />
                <ResultBar q="Q3" pct={38} tone="brand-300" />
              </div>
            }
          />
        </section>

        {/* ── 6. How it works ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <Kicker>How it works</Kicker>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-[28px]">
            {HOW_IT_WORKS.map((step) => (
              <div key={step.n}>
                <p className="text-[15px] font-extrabold [font-variant-numeric:tabular-nums]">{step.n}</p>
                <h3 className="mt-[10px] text-[18px] font-extrabold tracking-[-0.015em]">{step.title}</h3>
                <p className="mt-[6px] text-[14px] leading-[24px] text-ink/[0.78]">{step.copy}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── 7. In the room ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] items-center gap-[clamp(32px,5vw,64px)]">
            <div>
              <Kicker>In the room</Kicker>
              <h2 className="text-[32px] font-extrabold leading-[1.12] tracking-[-0.015em]">
                Built for the room, not the browser tab
              </h2>
              <p className="mt-[16px] max-w-[52ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                Join codes big enough for the back row, questions that read on a
                phone held at arm&apos;s length, and results on the projector
                before the bell — or the coffee refill.
              </p>
            </div>
            <div className="aspect-[951/665] w-full overflow-hidden border-2 border-divider">
              <Image
                src="/images/hquiz1.png"
                alt="Quizwerk running a live quiz on a projector"
                width={951}
                height={665}
                className="h-full w-full object-cover [filter:grayscale(1)_contrast(1.08)]"
              />
            </div>
          </div>
        </section>

        {/* ── 8. Pricing ── */}
        <section id="pricing" className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <Kicker>Pricing</Kicker>
          <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
            Pick a plan that fits how you train
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
                <h3 className="text-[20px] font-extrabold tracking-[-0.015em]">{plan.name}</h3>
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
                    <li key={feature} className="flex items-center gap-[12px] text-[15px]">
                      <span className="h-[8px] w-[8px] flex-none bg-brand" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <div>
                  <button
                    type="button"
                    onClick={() => handlePlanSelection(plan.action)}
                    disabled={activePlan === plan.action || isCurrentPlan(plan.action)}
                    className={`${plan.featured ? BTN_PRIMARY : BTN_GHOST} disabled:cursor-not-allowed disabled:opacity-60`}
                  >
                    {isCurrentPlan(plan.action)
                      ? "Current plan"
                      : activePlan === plan.action
                        ? "Redirecting…"
                        : plan.cta}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── 9. Testimonials ── */}
        <section className={`${CONTAINER} border-t-2 border-divider py-[70px]`}>
          <Kicker>From classrooms and boardrooms</Kicker>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[36px]">
            {TESTIMONIALS.map((t) => (
              <figure key={t.who} className="border-t-2 border-divider pt-[20px]">
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
              The next quiz writes itself.
            </h3>
            <button
              type="button"
              onClick={goGenerate}
              className={`${BTN_INVERSE} mt-[32px]`}
            >
              Generate your first quiz — free
            </button>
          </div>
        </section>
      </main>

      {/* ── 11. Footer ── */}
      <footer className={`${CONTAINER} flex flex-wrap items-center justify-between gap-x-[28px] gap-y-[12px] py-[28px] text-[13px] text-ink/70`}>
        <span className="text-[15px] font-extrabold tracking-[-0.015em] text-ink">Quizwerk</span>
        <span className="flex flex-wrap gap-x-[24px] gap-y-[8px]">
          <a href="#product" className="min-h-[44px] content-center hover:text-brand">Product</a>
          <a href="#categories" className="min-h-[44px] content-center hover:text-brand">Categories</a>
          <a href="#pricing" className="min-h-[44px] content-center hover:text-brand">Pricing</a>
          <button type="button" onClick={goJoin} className="min-h-[44px] cursor-pointer hover:text-brand">
            Join a live quiz
          </button>
        </span>
        <span>© 2026 Quizwerk. All rights reserved.</span>
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
