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
import { usePersona } from "@features/persona/context/personaContext";
import NotificationBell from "@features/notifications/components/NotificationBell";
import { archivo, BTN_PRIMARY } from "@shared/ui/quizwerk";

/**
 * Primary navigation, in the Quizwerk design language.
 *
 * The desktop and mobile menus render from this one list — they used to be
 * two hand-maintained copies that drifted.
 */
type NavItem =
  | { kind: "link"; label: string; href: string; authOnly?: boolean }
  | { kind: "action"; label: string; action: "browse" };

const NAV_ITEMS: NavItem[] = [
  { kind: "link", label: "Home", href: "/" },
  { kind: "link", label: "Dashboard", href: "/dashboard", authOnly: true },
  { kind: "link", label: "Generate Quiz", href: "/generate" },
  { kind: "action", label: "Categories", action: "browse" },
  { kind: "link", label: "Pricing", href: "/#pricing" },
];

/** Signed-in shortcuts, shown only in the mobile drawer. */
const MOBILE_WORKSPACE_LINKS = [
  { label: "My Profile", href: "/profile" },
  { label: "Saved Quizzes", href: "/saved_quiz" },
  { label: "Popular Quizzes", href: "/popular" },
  { label: "Folders", href: "/folders" },
  { label: "Quiz History", href: "/quiz_history" },
];

const NavBar: React.FC = () => {
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const { definition: personaDefinition } = usePersona();

  const router = useRouter();

  const switchToSignIn = () => {
    setIsSignUpOpen(false);
    setIsLoginOpen(true);
  };

  const switchToSignUp = () => {
    setIsLoginOpen(false);
    setIsSignUpOpen(true);
  };

  const isActive = (href: string) => {
    if (href === "/") {
      return router.pathname === "/" && !router.asPath.includes("#");
    }
    if (href.startsWith("/#")) {
      return router.asPath.endsWith(href.slice(1));
    }
    return router.pathname === href;
  };

  const visibleItems = NAV_ITEMS.filter(
    (item) => !("authOnly" in item && item.authOnly) || isAuthenticated,
  );

  return (
    <div className={archivo.className}>
      {!isLoading && isAuthenticated && (
        <>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            aria-label="Toggle workspace sidebar"
            className="fixed left-4 top-4 z-[100] hidden bg-brand p-2 text-paper transition hover:bg-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand md:flex"
          >
            {isSidebarOpen ? <X /> : <Menu />}
          </button>

          <div
            className={`fixed left-0 top-0 z-50 h-full border-r-2 border-divider bg-paper transition-all duration-300 ${
              isSidebarOpen ? "w-64" : "w-0 overflow-hidden"
            }`}
            style={{ paddingTop: "64px" }}
          >
            <Sidebar onBrowseClick={() => setIsBrowseModalOpen(true)} />
          </div>
        </>
      )}

      <nav className="fixed left-0 right-0 top-0 z-40 flex h-16 items-center border-b-2 border-divider bg-paper">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-[clamp(20px,5vw,72px)]">
          <Link
            href="/"
            className="text-[18px] font-extrabold tracking-[-0.015em] text-ink"
          >
            Quizwerk
          </Link>

          <div className="hidden items-center gap-[28px] md:flex">
            {visibleItems.map((item) =>
              item.kind === "link" ? (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`text-[15px] transition ${
                    isActive(item.href)
                      ? "font-extrabold text-brand"
                      : "text-ink hover:text-brand"
                  }`}
                >
                  {item.label}
                </Link>
              ) : (
                <button
                  key={item.label}
                  onClick={() => setIsBrowseModalOpen(true)}
                  className={`text-[15px] transition ${
                    isBrowseModalOpen
                      ? "font-extrabold text-brand"
                      : "text-ink hover:text-brand"
                  }`}
                >
                  {item.label}
                </button>
              ),
            )}
          </div>

          <div className="hidden items-center gap-[16px] md:flex">
            <NavGenerateQuizButton />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <>
                    <NotificationBell />
                    <span className="text-[15px] text-ink">
                      Hi, {user?.username || "User"}
                      {personaDefinition ? (
                        <span className="ml-[6px] text-[13px] text-ink/60">
                          · {personaDefinition.label}
                        </span>
                      ) : null}
                    </span>
                    <button onClick={logout} className={BTN_PRIMARY}>
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
            className="p-2 text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand md:hidden"
            aria-label="Toggle mobile top-nav"
          >
            {isMobileNavOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      <div className="h-16" />

      <div
        className={`fixed left-0 top-16 z-30 max-h-[calc(100vh-64px)] w-full overflow-y-auto border-b-2 border-divider bg-paper transition-transform duration-200 md:hidden ${
          isMobileNavOpen ? "translate-y-0" : "-translate-y-full"
        }`}
      >
        <div className="flex flex-col px-4 py-4">
          {visibleItems.map((item) =>
            item.kind === "link" ? (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setIsMobileNavOpen(false)}
                className={`min-h-[44px] content-center border-t-2 border-divider px-3 py-2 text-[16px] transition ${
                  isActive(item.href)
                    ? "font-extrabold text-brand"
                    : "text-ink hover:bg-ink/[0.05]"
                }`}
              >
                {item.label}
              </Link>
            ) : (
              <button
                key={item.label}
                onClick={() => {
                  setIsMobileNavOpen(false);
                  setIsBrowseModalOpen(true);
                }}
                className="min-h-[44px] border-t-2 border-divider px-3 py-2 text-left text-[16px] text-ink transition hover:bg-ink/[0.05]"
              >
                {item.label}
              </button>
            ),
          )}

          {!isLoading && isAuthenticated && (
            <>
              <p className="mb-1 mt-4 px-3 text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
                Workspace
              </p>
              {MOBILE_WORKSPACE_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setIsMobileNavOpen(false)}
                  className="min-h-[44px] content-center border-t-2 border-divider px-3 py-2 text-[16px] text-ink transition hover:bg-ink/[0.05]"
                >
                  {link.label}
                </Link>
              ))}
            </>
          )}

          <div className="mt-4 flex flex-col gap-3 border-t-2 border-divider pt-4">
            <NavGenerateQuizButton className="w-full text-center" />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <>
                    <span className="text-center text-[15px] text-ink">
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
                      className={`${BTN_PRIMARY} w-full`}
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
    </div>
  );
};

export default NavBar;
