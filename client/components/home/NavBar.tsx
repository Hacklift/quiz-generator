// components/home/NavBar.tsx
"use client";

import React, { useState } from "react";
import Link from "next/link";
import SignInButton from "./SignInButton";
import SignUpButton from "./SignUpButton";
import SignUpModal from "../(dashboard)/user/SignUpModal";
import LoginModal from "../(dashboard)/user/SignInModal";
import QuizDropdown from "./QuizDropdown";
import PricingLink from "./PricingLink";
import HowItWorksLink from "./HowItWorksLink";
import NavGenerateQuizButton from "./NavGenerateQuizButton";
import Sidebar from "./Sidebar";
import BrowseModal from "./modals/BrowseModal";

import { Menu, X } from "lucide-react";

const NavBar: React.FC = () => {
  // Modal state
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);

  // Callbacks for switching between modals
  const switchToSignIn = () => {
    setIsSignUpOpen(false);
    setIsLoginOpen(true);
  };
  const switchToSignUp = () => {
    setIsLoginOpen(false);
    setIsSignUpOpen(true);
  };

  // Sidebar toggle (unchanged)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Mobile top‑nav dropdown toggle
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <>
      {/* ── 1) Sidebar Toggle Button (always visible) ── */}
      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="fixed top-4 left-4 z-[100] text-[#0F2654] text-2xl focus:outline-none bg-[#E0E2E5] p-2 rounded-full shadow-md"
      >
        {isSidebarOpen ? <X /> : <Menu />}
      </button>

      {/* ── 2) Sidebar itself (always in the DOM, unchanged) ── */}
      <div
        className={`
          fixed top-0 left-0 h-full bg-[#F5F5F5] shadow-md z-50
          transition-all duration-300
          ${isSidebarOpen ? "w-64" : "w-0 overflow-hidden"}
        `}
        style={{ paddingTop: "64px" }}
      >
        <Sidebar onBrowseClick={() => setIsBrowseModalOpen(true)} />
      </div>

      {/* ── 3) Top Navigation Bar ── */}
      <nav className="bg-[#E0E2E5] shadow-md fixed top-0 left-0 right-0 z-40 h-16 flex items-center">
        <div className="max-w-6xl w-full mx-auto px-4 sm:px-6 md:px-8 flex items-center justify-between">
          {/* Logo (always visible) */}
          <Link
            href="/"
            className="text-2xl sm:text-3xl font-bold text-[#0F2654]"
          >
            HQuiz
          </Link>

          {/* ── Desktop/Tablet Links (hidden on small screens) ── */}
          <div className="hidden md:flex items-center space-x-8">
            <QuizDropdown />
            <PricingLink />
            <HowItWorksLink />
          </div>

          {/* ── Desktop/Tablet Buttons (hidden on small screens) ── */}
          <div className="hidden md:flex items-center space-x-4">
            <NavGenerateQuizButton />
            <SignInButton onOpen={() => setIsLoginOpen(true)} />
            <SignUpButton onOpen={() => setIsSignUpOpen(true)} />
          </div>

          {/* ── Mobile “hamburger” for top‑nav items (visible only on small screens) ── */}
          <button
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
            className="md:hidden text-[#0F2654] text-2xl focus:outline-none p-2 rounded-full"
            aria-label="Toggle mobile top-nav"
          >
            {isMobileNavOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      {/* ── 4) Spacer below NavBar so page content doesn’t hide under it ── */}
      <div className="h-16" />

      {/* ── 5) Mobile Top‑Nav Dropdown (slides down under NavBar) ── */}
      <div
        className={`
          fixed top-16 left-0 w-full bg-white shadow-md z-30
          md:hidden transition-transform duration-200
          ${isMobileNavOpen ? "translate-y-0" : "-translate-y-full"}
        `}
      >
        <div className="flex flex-col px-4 py-4 space-y-4">
          {/* Center Links */}
          <QuizDropdown />
          <PricingLink />
          <HowItWorksLink />

          {/* Divider */}
          <div className="border-t border-gray-200 my-2" />

          {/* Right‑side Buttons */}
          <NavGenerateQuizButton className="w-full text-center" />
          <SignInButton
            onOpen={() => setIsLoginOpen(true)}
            className="w-full text-center"
          />
          <SignUpButton
            onOpen={() => setIsSignUpOpen(true)}
            className="w-full text-center"
          />
        </div>
      </div>

      {/* ── 6) Modals ── */}
      <SignUpModal
        isOpen={isSignUpOpen}
        onClose={() => setIsSignUpOpen(false)}
        switchToSignIn={switchToSignIn}
      />
      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        switchToSignUp={switchToSignUp}
      />
      <BrowseModal
        isOpen={isBrowseModalOpen}
        onClose={() => setIsBrowseModalOpen(false)}
      />
    </>
  );
};

export default NavBar;
