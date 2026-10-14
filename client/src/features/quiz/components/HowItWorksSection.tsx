import { useTranslation } from "react-i18next";
import React from "react";

export default function HowItWorksSection() {
  const { t: uiText } = useTranslation("ui");

  const steps = [
    {
      step: "Step 1",
      title: uiText("md7effddc0e75a6d8"),
      desc: "Type in a subject or topic you want to create a quiz about—anything from science to history!",
    },
    {
      step: "Step 2",
      title: uiText("mb2d48240aa0f425a"),
      desc: "Select the format you need: multiple choice, true/false, or short answer questions.",
    },
    {
      step: "Step 3",
      title: uiText("mbe67bed1b59e7fad"),
      desc: "Click the 'Generate' button and watch as the AI instantly creates a set of questions and answers.",
    },
    {
      step: "Step 4",
      title: uiText("m956d78fcedd2effb"),
      desc: "Review your quiz, make any edits if needed, and save or download it to share with others!",
    },
  ];

  return (
    <section id="how-it-works" className="bg-gray-100 py-12 px-4">
      <h2 className="text-2xl font-bold text-center mb-10">
        {uiText("mc1879525c75cb5c2")}
      </h2>
      <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-6">
        {steps.map((stepObj, i) => (
          <div key={i} className="bg-white p-6 rounded shadow-md">
            <p className="font-bold mb-1">{stepObj.step}</p>
            <h3 className="text-md font-semibold mb-2">{stepObj.title}</h3>
            <p className="text-sm text-gray-600">{stepObj.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
