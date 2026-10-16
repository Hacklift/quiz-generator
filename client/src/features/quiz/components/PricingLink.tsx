"use client";
import { useTranslation } from "react-i18next";

import React from "react";
import Link from "next/link";

const PricingLink: React.FC = () => {
  const { t: uiText } = useTranslation("ui");
  return (
    <Link
      href="/#pricing"
      scroll={true}
      className="text-base font-semibold text-black hover:opacity-80 transition"
    >
      {uiText("mdfe95783edfef791")}
    </Link>
  );
};

export default PricingLink;
