"use client";

import React from "react";
import Link from "next/link";

const PricingLink: React.FC = () => (
  <Link
    href="/#pricing"
    scroll={true}
    className="text-base font-semibold text-black hover:opacity-80 transition"
  >
    Pricing
  </Link>
);

export default PricingLink;
