import { useTranslation } from "react-i18next";
import React from "react";

export default function TestimonialsSection() {
  const { t: uiText } = useTranslation("ui");

  return (
    <section className="py-12 bg-white">
      <h2 className="text-2xl font-semibold mb-8 text-center">
        {uiText("md2825cb6bc912314")}
      </h2>
      <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
        {Array(3)
          .fill(0)
          .map((_, i) => (
            <div key={i} className="bg-gray-100 p-6 rounded">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-gray-300" />
                <div className="text-left">
                  <p className="font-semibold text-sm">
                    {uiText("m79c181c04d6a3c2b")}
                  </p>
                  <p className="text-xs text-gray-500">
                    {uiText("m708428070fa387da")}
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-700 text-left">
                {uiText("mc53c0b31eaa4eadb")}
              </p>
            </div>
          ))}
      </div>
    </section>
  );
}
