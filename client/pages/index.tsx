"use client";

import React from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";
import PricingSection from "../components/home/PricingSection";
import TestimonialsSection from "../components/home/TestimonialsSection";
import HowItWorksSection from "../components/home/HowItWorksSection";

export default function Home() {
  const router = useRouter();

  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />

      <main className="flex-grow">
        {/* ───── HERO ───── */}
        <section className="bg-white text-center px-4 sm:px-6 md:px-8 py-12 md:py-16">
          <h1 className="font-bold text-2xl sm:text-3xl md:text-4xl lg:text-5xl mb-4">
            Instant <span className="text-[#0F2654]">Quizzes</span>, Smart{" "}
            <span className="text-[#0F2654]">Answers</span>
          </h1>
          <p className="text-sm sm:text-base md:text-lg text-gray-600 mb-6 max-w-xl mx-auto">
            Create engaging quizzes and get answers in seconds. Make learning
            fun and effortless!
          </p>
          <button
            onClick={() => router.push("/generate")}
            className="
              bg-[#0F2654] text-white 
              px-5 py-2 rounded-2xl 
              text-sm sm:text-base md:text-lg 
              hover:bg-[#0C2142] transition
            "
          >
            Get Started for Free
          </button>
        </section>

        {/* ───── ILLUSTRATION ───── */}
        <div className="w-full px-4 sm:px-6 md:px-8 mb-12">
          <div className="mx-auto max-w-screen-md">
            <Image
              src="/images/hquiz1.png"
              alt="Quiz Example"
              width={1000}
              height={500}
              className="w-full h-auto rounded-lg shadow"
            />
          </div>
        </div>

        {/* ───── QUIZ CARDS ───── */}
        <section className="px-4 sm:px-6 md:px-8 py-8 md:py-12 max-w-screen-lg mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold mb-8 text-center">
            Quiz Here
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: "Generate Quiz",
                desc: "Effortlessly create customized quizzes on any topic. Our smart quiz generator crafts tailored questions on any subject.",
                img: "/images/hquiz2.png",
              },
              {
                title: "Your Quiz Result",
                desc: "Display all generated quizzes with answers. Export quiz to PDF, text or platform format if applicable.",
                img: "/images/hquiz3.png",
              },
              {
                title: "Explore Template",
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
                    Learn More
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
