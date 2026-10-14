"use client";
import { useTranslation } from "react-i18next";

import React from "react";
import Link from "next/link";

const HowItWorksLink: React.FC = () => {
  const { t: uiText } = useTranslation("ui");
  return (
    <Link
      href="/#how-it-works"
      scroll={true}
      className="text-base font-semibold text-black hover:opacity-80 transition"
    >
      {uiText("mc1879525c75cb5c2")}
    </Link>
  );
};

export default HowItWorksLink;
