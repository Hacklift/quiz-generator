"use client";

import Link from "next/link";
import {
  FaGithub,
  FaInstagram,
  FaLinkedinIn,
  FaXTwitter,
} from "react-icons/fa6";

const footerSections = [
  {
    title: "Product",
    links: [
      { label: "Generate Quiz", href: "/generate" },
      { label: "Pricing", href: "/#pricing" },
      { label: "Popular Quizzes", href: "/popular" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Profile", href: "/profile" },
      { label: "Saved Quizzes", href: "/saved_quiz" },
      { label: "Quiz History", href: "/quiz_history" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "Billing History", href: "/billing_history" },
      { label: "How It Works", href: "/#how-it-works" },
      { label: "Reset Password", href: "/auth/request-reset-password" },
    ],
  },
];

const socialLinks = [
  { label: "GitHub", href: "https://github.com", icon: FaGithub },
  { label: "X", href: "https://x.com", icon: FaXTwitter },
  { label: "LinkedIn", href: "https://linkedin.com", icon: FaLinkedinIn },
  { label: "Instagram", href: "https://instagram.com", icon: FaInstagram },
];

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-[#8fb0d8]/20 bg-[#0F2654] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-12">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_repeat(3,1fr)]">
          <div className="max-w-md">
            <div className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/10 px-4 py-2 shadow-sm">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-sm font-bold text-[#0F2654]">
                HQ
              </span>
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-white/70">
                  Quiz Platform
                </p>
                <p className="text-lg font-semibold text-white">HQuiz</p>
              </div>
            </div>

            <p className="mt-5 text-sm leading-7 text-white/80">
              Build cleaner quizzes, organize what matters, and manage billing
              from one place. HQuiz is designed to keep content creation and
              subscription management straightforward.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              {socialLinks.map(({ label, href, icon: Icon }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={label}
                  className={`inline-flex h-11 w-11 items-center justify-center rounded-full border shadow-sm transition hover:-translate-y-0.5 ${
                    label === "GitHub"
                      ? "border-white/15 bg-white text-[#111827] hover:bg-[#f3f4f6]"
                      : label === "X"
                        ? "border-[#1DA1F2]/35 bg-[#1DA1F2] text-white hover:bg-[#0c8bdc]"
                        : label === "LinkedIn"
                          ? "border-[#0A66C2]/35 bg-[#0A66C2] text-white hover:bg-[#08539c]"
                          : "border-[#E1306C]/35 bg-[linear-gradient(135deg,#F58529_0%,#E1306C_55%,#833AB4_100%)] text-white hover:opacity-90"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          {footerSections.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-white/75">
                {section.title}
              </h3>
              <ul className="mt-4 space-y-3">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-white/80 transition hover:text-white"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-white/10 pt-6 text-sm text-white/70 md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} HQuiz. All rights reserved.</p>
          <div className="flex flex-wrap gap-5">
            <span>Powered by Stripe test mode and app-managed plans</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
