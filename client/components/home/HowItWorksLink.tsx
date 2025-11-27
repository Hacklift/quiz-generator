"use client";

import React from "react";
import Link from "next/link";

const HowItWorksLink: React.FC = () => (
  <Link
    href="/#how-it-works"
    scroll={true}
    className="text-base font-semibold text-black hover:opacity-80 transition"
  >
    How It Works
  </Link>
);

export default HowItWorksLink;
