"use client";

import React from "react";
import Link from "next/link";
import { FaGithub, FaTwitter, FaLinkedin } from "react-icons/fa";

const footerSections = [
  {
    title: "Explore",
    links: [
      { label: "Generate Quiz", href: "/generate" },
      { label: "Popular Quizzes", href: "/popular" },
      { label: "Join Live Quiz", href: "/quiz-access" },
    ],
  },
  {
    title: "Workspace",
    links: [
      { label: "Saved Quizzes", href: "/saved_quiz" },
      { label: "Quiz History", href: "/quiz_history" },
      { label: "Folders", href: "/folders" },
    ],
  },
];

const socialLinks = [
  {
    label: "GitHub",
    href: "https://github.com/your-repo",
    icon: FaGithub,
  },
  {
    label: "Twitter",
    href: "https://twitter.com/your-handle",
    icon: FaTwitter,
  },
  {
    label: "LinkedIn",
    href: "https://linkedin.com/in/your-profile",
    icon: FaLinkedin,
  },
];

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-8 bg-gray-900 text-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="grid grid-cols-1 gap-8 min-[520px]:grid-cols-2 lg:grid-cols-[1.35fr_1fr_1fr_1fr] lg:gap-10">
          <div className="min-[520px]:col-span-2 lg:col-span-1 lg:max-w-sm">
            <Link
              href="/"
              className="inline-flex text-lg font-semibold tracking-normal text-white transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              HQuiz
            </Link>
            <p className="mt-3 max-w-md text-sm leading-6 text-gray-400">
              Create, organize, and share quizzes for learning sessions that
              work across every screen size.
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
            <h2 className="text-sm font-semibold text-white">Connect</h2>
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
            © {currentYear} HQuiz. All rights reserved.
          </p>
          <div className="mt-4 flex flex-col gap-2 min-[420px]:flex-row min-[420px]:flex-wrap min-[420px]:gap-x-5 sm:mt-0">
            <Link
              href="/auth/login"
              className="inline-flex min-h-8 items-center text-sm text-gray-400 transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              Sign in
            </Link>
            <Link
              href="/auth/register"
              className="inline-flex min-h-8 items-center text-sm text-gray-400 transition hover:text-blue-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-300"
            >
              Create account
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
