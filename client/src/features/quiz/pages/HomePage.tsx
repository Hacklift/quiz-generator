"use client";
import { useTranslation } from "react-i18next";

import React from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import { Radio, Users } from "lucide-react";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import PricingSection from "@features/quiz/components/PricingSection";
import TestimonialsSection from "@features/quiz/components/TestimonialsSection";
import HowItWorksSection from "@features/quiz/components/HowItWorksSection";

export default function Home() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();

  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />

      <main className="flex-grow">
        {/* ───── HERO ───── */}
        <section className="bg-white text-center px-4 sm:px-6 md:px-8 py-12 md:py-16">
          <h1 className="font-bold text-2xl sm:text-3xl md:text-4xl lg:text-5xl mb-4">
            {uiText("me2861894f065ab75")}
            <span className="text-[#0F2654]">
              {uiText("mf1e638bae6e83167")}
            </span>
            {uiText("m4b866271e5c93f13")}{" "}
            <span className="text-[#0F2654]">
              {uiText("m4ad0a0a6ae56d6bc")}
            </span>
          </h1>
          <p className="text-sm sm:text-base md:text-lg text-gray-600 mb-6 max-w-xl mx-auto">
            {uiText("me09481aabb728cca")}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={() => router.push("/generate")}
              className="
                inline-flex items-center justify-center gap-2
                bg-[#0F2654] text-white
                px-5 py-2 rounded-md
                text-sm sm:text-base md:text-lg font-semibold
                hover:bg-[#0C2142] transition
              "
            >
              <Radio size={18} aria-hidden="true" />
              {uiText("ma0e3a9103479ddfc")}
            </button>
            <button
              onClick={() => router.push("/quiz-access")}
              className="
                inline-flex items-center justify-center gap-2
                border border-[#0F2654] text-[#0F2654] bg-white
                px-5 py-2 rounded-md
                text-sm sm:text-base md:text-lg font-semibold
                hover:bg-slate-50 transition
              "
            >
              <Users size={18} aria-hidden="true" />
              {uiText("m90330531b0455f3e")}
            </button>
          </div>
        </section>

        {/* ───── ILLUSTRATION ───── */}
        <div className="w-full px-4 sm:px-6 md:px-8 mb-12">
          <div className="mx-auto max-w-screen-md">
            <Image
              src="/images/hquiz1.png"
              alt={uiText("mfa5b9f193df54b21")}
              width={1000}
              height={500}
              className="w-full h-auto rounded-lg shadow"
            />
          </div>
        </div>

        {/* ───── QUIZ CARDS ───── */}
        <section className="px-4 sm:px-6 md:px-8 py-8 md:py-12 max-w-screen-lg mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold mb-8 text-center">
            {uiText("mde53383db46551cc")}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: uiText("m5da69270e5973c17"),
                desc: "Effortlessly create customized quizzes on any topic. Our smart quiz generator crafts tailored questions on any subject.",
                img: "/images/hquiz2.png",
              },
              {
                title: uiText("m8375f132f4d8767d"),
                desc: "Display all generated quizzes with answers. Export quiz to PDF, text or platform format if applicable.",
                img: "/images/hquiz3.png",
              },
              {
                title: uiText("m2eab8d4ec8a9f654"),
                desc: "Users can input one question for quick answers. Shows AI-generated answers immediately below input.",
                img: "/images/hquiz4.png",
              },
            ].map((item, i) => (
              <div
                key={i}
                className="
                  bg-white rounded-lg shadow-md 
                  flex flex-col 
                  overflow-hidden
                "
              >
                <div className="h-40 md:h-48 w-full relative">
                  <Image
                    src={item.img}
                    alt={item.title}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    className="object-cover"
                  />
                </div>
                <div className="p-4 flex flex-col flex-1">
                  <h3 className="font-semibold text-lg text-[#0F2654] mb-2">
                    {item.title}
                  </h3>
                  <p className="text-sm text-gray-600 flex-1">{item.desc}</p>
                  <p className="mt-4 text-[#0F2654] text-sm font-medium cursor-pointer hover:underline">
                    {uiText("m8d8cd546b58d91c3")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ───── HOW IT WORKS ───── */}
        <HowItWorksSection />

        {/* ───── PRICING & TESTIMONIALS ───── */}
        <div className="px-4 sm:px-6 md:px-8">
          <PricingSection />
          <TestimonialsSection />
        </div>
      </main>

      <Footer />
    </div>
  );
}
