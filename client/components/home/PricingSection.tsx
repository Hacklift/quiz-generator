import React from "react";

const plans = [
  {
    plan: "Free",
    price: "$0",
    features: [
      "Generate up to 5 quizzes per month",
      "Basic question types",
      "Save and share quizzes",
      "Access to community quiz templates",
    ],
  },
  {
    plan: "Monthly",
    price: "$9.99",
    features: [
      "Unlimited quiz generation",
      "Advanced question types",
      "Edit and customize questions",
      "Export in multiple formats",
      "Priority support",
    ],
  },
  {
    plan: "Yearly",
    price: "$99 (save 20%)",
    features: [
      "All monthly subscription benefits",
      "Early access to new features",
      "Personalized templates",
      "Premium support",
    ],
  },
];

export default function PricingSection() {
  return (
    <section id="pricing" className="py-12 bg-[#f4f4f4]">
      <h2 className="text-2xl font-semibold mb-8 text-center">Pricing</h2>
      <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
        {plans.map(({ plan, price, features }, i) => (
          <div
            key={i}
            className="bg-white rounded shadow-md p-6 text-left flex flex-col"
          >
            <h3 className="text-xl font-bold mb-2">{plan}</h3>
            <p className="text-[#0F2654] font-semibold mb-4">{price}</p>
            <ul className="text-sm text-gray-700 list-disc list-inside mb-6 flex-1">
              {features.map((f, idx) => (
                <li key={idx}>{f}</li>
              ))}
            </ul>
            <button className="w-full bg-[#0F2654] text-white py-3 rounded-2xl hover:bg-[#0C2142] transition">
              Get Started
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
