"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import SignInButton from "./SignInButton";
import SignUpButton from "./SignUpButton";
import SignUpModal from "../auth/SignUpModal";
import SignInModal from "../auth/SignInModal";
import QuizDropdown from "./QuizDropdown";
import PricingLink from "./PricingLink";
import HowItWorksLink from "./HowItWorksLink";
import NavGenerateQuizButton from "./NavGenerateQuizButton";
import Sidebar from "./Sidebar";
import BrowseModal from "./modals/BrowseModal";
import { useAuth } from "../../contexts/authContext";

const NavBar: React.FC = () => {
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const { user, isAuthenticated, logout, isLoading } = useAuth();

  const switchToSignIn = () => {
    setIsSignUpOpen(false);
    setIsLoginOpen(true);
  };

  const switchToSignUp = () => {
    setIsLoginOpen(false);
    setIsSignUpOpen(true);
  };

  return (
    <>
      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="fixed top-4 left-4 z-[100] text-[#0F2654] text-2xl focus:outline-none bg-[#E0E2E5] p-2 rounded-full shadow-md"
      >
        {isSidebarOpen ? <X /> : <Menu />}
      </button>

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

      <nav className="bg-[#E0E2E5] shadow-md fixed top-0 left-0 right-0 z-40 h-16 flex items-center">
        <div className="max-w-6xl w-full mx-auto px-4 sm:px-6 md:px-8 flex items-center justify-between">
          <Link
            href="/"
            className="text-2xl sm:text-3xl font-bold text-[#0F2654]"
          >
            HQuiz
          </Link>

          <div className="hidden md:flex items-center space-x-8">
            <QuizDropdown />
            <PricingLink />
            <HowItWorksLink />
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <NavGenerateQuizButton />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <>
                    <span className="text-[#0F2654] font-medium">
                      Hi, {user?.username || "User"} 👋
                    </span>
                    <button
                      onClick={logout}
                      className="bg-[#0F2654] text-white px-4 py-2 rounded-lg hover:bg-[#173773] transition-all"
                    >
                      Logout
                    </button>
                  </>
                ) : (
                  <>
                    <SignInButton onOpen={() => setIsLoginOpen(true)} />
                    <SignUpButton onOpen={() => setIsSignUpOpen(true)} />
                  </>
                )}
              </>
            )}
          </div>

          <button
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
            className="md:hidden text-[#0F2654] text-2xl focus:outline-none p-2 rounded-full"
            aria-label="Toggle mobile top-nav"
          >
            {isMobileNavOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      <div className="h-16" />

      <div
        className={`
          fixed top-16 left-0 w-full bg-white shadow-md z-30
          md:hidden transition-transform duration-200
          ${isMobileNavOpen ? "translate-y-0" : "-translate-y-full"}
        `}
      >
        <div className="flex flex-col px-4 py-4 space-y-4">
          <QuizDropdown />
          <PricingLink />
          <HowItWorksLink />
          <div className="border-t border-gray-200 my-2" />
          <NavGenerateQuizButton className="w-full text-center" />
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <span className="text-[#0F2654] text-center">
                    Hi, {user?.username || "User"} 👋
                  </span>
                  <button
                    onClick={() => {
                      logout();
                      setIsMobileNavOpen(false);
                    }}
                    className="bg-[#0F2654] text-white px-4 py-2 rounded-lg hover:bg-[#173773] transition-all w-full"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <SignInButton
                    onOpen={() => setIsLoginOpen(true)}
                    className="w-full text-center"
                  />
                  <SignUpButton
                    onOpen={() => setIsSignUpOpen(true)}
                    className="w-full text-center"
                  />
                </>
              )}
            </>
          )}
        </div>
      </div>

      <SignUpModal
        isOpen={isSignUpOpen}
        onClose={() => setIsSignUpOpen(false)}
        switchToSignIn={switchToSignIn}
      />
      <SignInModal
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
