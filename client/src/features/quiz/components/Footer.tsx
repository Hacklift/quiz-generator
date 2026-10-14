"use client";
import { useTranslation } from "react-i18next";

import React from "react";
import Link from "next/link";
import { FaGithub, FaTwitter, FaLinkedin } from "react-icons/fa";
import { useTerms } from "@features/persona/hooks/useTerms";
import { titleCaseTerm } from "@shared/config/terminology";

export default function Footer() {
  const { t: uiText } = useTranslation("ui");

  const socialLinks = [
    {
      label: uiText("mf911e414cf6bdfc5"),
      href: "https://github.com/your-repo",
      icon: FaGithub,
    },
    {
      label: uiText("mbcd18ead5fa83012"),
      href: "https://twitter.com/your-handle",
      icon: FaTwitter,
    },
    {
      label: uiText("mdd84425b72da12c6"),
      href: "https://linkedin.com/in/your-profile",
      icon: FaLinkedin,
    },
  ];

  const currentYear = new Date().getFullYear();
  const t = useTerms();
  const footerSections = [
    {
      title: uiText("m3b73900b8d29f963"),
      links: [
        {
          label: uiText("m37a7e45e1b49df1f", { value0: t("quiz") }),
          href: "/generate",
        },
        {
          label: uiText("m8f69b479b1efca68", { value0: t("quiz", "plural") }),
          href: "/popular",
        },
        {
          label: uiText("m0b8eeac901367065", { value0: t("live_quiz") }),
          href: "/quiz-access",
        },
      ],
    },
    {
      title: uiText("m87bb59ba2f92f2a5"),
      links: [
        {
          label: uiText("mce0983f3577f5ce9", { value0: t("quiz", "plural") }),
          href: "/saved_quiz",
        },
        {
          label: uiText("m0d6eb040a81b42bb", {
            value0: titleCaseTerm(t("quiz")),
          }),
          href: "/quiz_history",
        },
        { label: uiText("mc4d6bb200f4c058a"), href: "/folders" },
      ],
    },
  ];

  return (
    <footer className="mt-8 bg-gray-900 text-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="grid grid-cols-1 gap-8 min-[520px]:grid-cols-2 lg:grid-cols-[1.35fr_1fr_1fr_1fr] lg:gap-10">
          <div className="min-[520px]:col-span-2 lg:col-span-1 lg:max-w-sm">
            <Link
              href="/"
              className="inline-flex text-lg font-semibold tracking-normal text-white transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              {uiText("ma836de7cc1743876")}
            </Link>
            <p className="mt-3 max-w-md text-sm leading-6 text-gray-400">
              {uiText("m487de636aa781055")}
            </p>
          </div>

          {footerSections.map((section) => (
            <nav key={section.title} aria-label={section.title}>
              <h2 className="text-sm font-semibold text-white">
                {section.title}
              </h2>
              <ul className="mt-4 space-y-3">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="inline-flex min-h-8 items-center text-sm text-gray-400 transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          <div>
            <h2 className="text-sm font-semibold text-white">
              {uiText("m1a2303ede07493ac")}
            </h2>
            <div className="mt-4 flex flex-wrap gap-3">
              {socialLinks.map(({ label, href, icon: Icon }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-gray-700 text-gray-300 transition hover:border-blue-300 hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
                >
                  <Icon size={20} aria-hidden="true" />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-gray-800 pt-6 sm:mt-10 sm:flex sm:items-center sm:justify-between sm:gap-4">
          <p className="text-sm text-gray-400">
            © {currentYear} {uiText("m85baf7e5f1e79d19")}
          </p>
          <div className="mt-4 flex flex-col gap-2 min-[420px]:flex-row min-[420px]:flex-wrap min-[420px]:gap-x-5 sm:mt-0">
            <Link
              href="/auth/login"
              className="inline-flex min-h-8 items-center text-sm text-gray-400 transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              {uiText("mbfd402b2f6f38125")}
            </Link>
            <Link
              href="/auth/register"
              className="inline-flex min-h-8 items-center text-sm text-gray-400 transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              {uiText("m798ca2ce18bf2038")}
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
