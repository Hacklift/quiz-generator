"use client";

import React, { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import SignInButton from "./SignInButton";
import SignUpButton from "./SignUpButton";
import SignUpModal from "@features/auth/components/SignUpModal";
import SignInModal from "@features/auth/components/SignInModal";
import NavGenerateQuizButton from "./NavGenerateQuizButton";
import Sidebar from "./Sidebar";
import BrowseModal from "./modals/BrowseModal";
import { useAuth } from "@features/auth/context/authContext";
import NotificationBell from "@features/notifications/components/NotificationBell";

const NavBar: React.FC = () => {
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { user, isAuthenticated, logout, isLoading } = useAuth();

  const router = useRouter();

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
      {!isLoading && isAuthenticated && (
        <>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="hidden md:flex fixed top-4 left-4 z-[100] text-[#0F2654] text-2xl focus:outline-none bg-[#E0E2E5] p-2 rounded-full shadow-md"
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
        </>
      )}

      <nav className="bg-[#E0E2E5] shadow-md fixed top-0 left-0 right-0 z-40 h-16 flex items-center">
        <div className="max-w-6xl w-full mx-auto px-4 sm:px-6 md:px-8 flex items-center justify-between">
          <Link
            href="/"
            className="text-2xl sm:text-3xl font-bold text-[#0F2654]"
          >
            HQuiz
          </Link>

          <div className="hidden md:flex items-center space-x-8">
            <Link
              href="/"
              className={`text-sm font-medium transition-all ${
                router.pathname === "/" && !router.asPath.includes("#")
                  ? "text-[#0F2654] font-semibold"
                  : "text-gray-500 hover:text-[#0F2654]"
              }`}
            >
              Home
            </Link>

            <Link
              href="/generate"
              className={`text-sm font-medium transition-all ${
                router.pathname === "/generate"
                  ? "text-[#0F2654] font-semibold"
                  : "text-gray-500 hover:text-[#0F2654]"
              }`}
            >
              Generate Quiz
            </Link>

            <button
              onClick={() => setIsBrowseModalOpen(true)}
              className={`text-sm font-medium transition-all ${
                isBrowseModalOpen
                  ? "text-[#0F2654] font-semibold"
                  : "text-gray-500 hover:text-[#0F2654]"
              }`}
            >
              Categories
            </button>

            <Link
              href="/#pricing"
              className={`text-sm font-medium transition-all ${
                router.asPath.endsWith("#pricing")
                  ? "text-[#0F2654] font-semibold"
                  : "text-gray-500 hover:text-[#0F2654]"
              }`}
            >
              Pricing
            </Link>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <NavGenerateQuizButton />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <>
                    <NotificationBell />
                    <span className="text-[#0F2654] font-medium">
                      Hi, {user?.username || "User"}
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
          md:hidden transition-transform duration-200 overflow-y-auto max-h-[calc(100vh-64px)]
          ${isMobileNavOpen ? "translate-y-0" : "-translate-y-full"}
        `}
      >
        <div className="flex flex-col px-4 py-4 space-y-4">
          <Link
            href="/"
            onClick={() => setIsMobileNavOpen(false)}
            className={`text-base font-medium px-3 py-2 rounded-md transition-all ${
              router.pathname === "/" && !router.asPath.includes("#")
                ? "bg-[#0F2654] text-white font-semibold shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Home
          </Link>

          <Link
            href="/generate"
            onClick={() => setIsMobileNavOpen(false)}
            className={`text-base font-medium px-3 py-2 rounded-md transition-all ${
              router.pathname === "/generate"
                ? "bg-[#0F2654] text-white font-semibold shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Generate Quiz
          </Link>

          <button
            onClick={() => {
              setIsMobileNavOpen(false);
              setIsBrowseModalOpen(true);
            }}
            className={`text-base font-medium px-3 py-2 rounded-md transition-all text-left ${
              isBrowseModalOpen
                ? "bg-[#0F2654] text-white font-semibold shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Categories
          </button>

          <Link
            href="/#pricing"
            onClick={() => setIsMobileNavOpen(false)}
            className={`text-base font-medium px-3 py-2 rounded-md transition-all ${
              router.asPath.endsWith("#pricing")
                ? "bg-[#0F2654] text-white font-semibold shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Pricing
          </Link>

          {!isLoading && isAuthenticated && (
            <>
              <div className="border-t border-gray-200 my-2 pt-2">
                <p className="px-3 text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  Dashboard Menu
                </p>
              </div>

              <Link
                href="/profile"
                onClick={() => setIsMobileNavOpen(false)}
                className="text-base font-medium px-3 py-2 rounded-md text-gray-600 hover:bg-gray-100 transition-all flex items-center gap-2"
              >
                👤 My Profile
              </Link>

              <Link
                href="/saved_quiz"
                onClick={() => setIsMobileNavOpen(false)}
                className="text-base font-medium px-3 py-2 rounded-md text-gray-600 hover:bg-gray-100 transition-all flex items-center gap-2"
              >
                💾 Saved Quizzes
              </Link>

              <Link
                href="/popular"
                onClick={() => setIsMobileNavOpen(false)}
                className="text-base font-medium px-3 py-2 rounded-md text-gray-600 hover:bg-gray-100 transition-all flex items-center gap-2"
              >
                🌟 Popular Quizzes
              </Link>

              <Link
                href="/folders"
                onClick={() => setIsMobileNavOpen(false)}
                className="text-base font-medium px-3 py-2 rounded-md text-gray-600 hover:bg-gray-100 transition-all flex items-center gap-2"
              >
                📁 Folders
              </Link>

              <Link
                href="/quiz_history"
                onClick={() => setIsMobileNavOpen(false)}
                className="text-base font-medium px-3 py-2 rounded-md text-gray-600 hover:bg-gray-100 transition-all flex items-center gap-2"
              >
                🕘 Quiz History
              </Link>
            </>
          )}

          <div className="border-t border-gray-200 my-2" />
          <NavGenerateQuizButton className="w-full text-center" />
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <span className="text-[#0F2654] text-center">
                    Hi, {user?.username || "User"}
                  </span>
                  <div className="flex justify-center">
                    <NotificationBell />
                  </div>
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
