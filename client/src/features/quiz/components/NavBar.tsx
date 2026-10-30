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
import { useAuth } from "@features/auth/context/authContext";
import { usePersona } from "@features/persona/context/personaContext";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  titleCaseTerm,
  type TerminologyResolver,
} from "@shared/config/terminology";
import { ROUTES } from "@shared/config/patterns/routes";
import NotificationBell from "@features/notifications/components/NotificationBell";
import { archivo, BTN_PRIMARY } from "@shared/ui/quizwerk";
import OrganizationSwitcher from "@features/organizations/components/OrganizationSwitcher";
import UpgradePlanButton from "./sidebar/UpgradePlanButton";

/**
 * Primary navigation, in the Quizwerk design language.
 *
 * The desktop and mobile menus render from this one list — they used to be
 * two hand-maintained copies that drifted.
 */
type NavItem = {
  kind: "link";
  label: string;
  href: string;
  authOnly?: boolean;
};

export function navigationItems(): NavItem[] {
  return [
    { kind: "link", label: "Home", href: "/" },
    { kind: "link", label: "Dashboard", href: "/dashboard", authOnly: true },
    { kind: "link", label: "Categories", href: ROUTES.CATEGORIES },
    { kind: "link", label: "Pricing", href: "/#pricing" },
  ];
}

function mobileWorkspaceLinks(t: TerminologyResolver) {
  return [
    { label: "My Profile", href: "/profile" },
    { label: `Saved ${t("quiz", "plural")}`, href: "/saved_quiz" },
    { label: `Popular ${t("quiz", "plural")}`, href: "/popular" },
    { label: "Folders", href: "/folders" },
    { label: `${titleCaseTerm(t("group", "plural"))} & assignments`, href: ROUTES.COHORTS },
    { label: titleCaseTerm(t("live_quiz", "plural")), href: "/my-live-quizzes" },
    { label: `${titleCaseTerm(t("quiz"))} history`, href: "/quiz_history" },
  ];
}

const NavBar: React.FC = () => {
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const { definition: personaDefinition } = usePersona();
  const t = useTerms();

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

  const visibleItems = navigationItems().filter(
    (item) => !("authOnly" in item && item.authOnly) || isAuthenticated,
  );
  const workspaceLinks = mobileWorkspaceLinks(t);

  return (
    <div className={archivo.className}>
      {!isLoading && isAuthenticated && isSidebarOpen && (
        <aside
          id="workspace-sidebar"
          aria-label="Workspace navigation"
          className="fixed bottom-0 left-0 top-16 z-50 hidden w-64 overflow-y-auto overscroll-contain border-r-2 border-divider bg-paper xl:block"
        >
          <Sidebar onBrowseClick={() => router.push(ROUTES.CATEGORIES)} />
        </aside>
      )}

      <nav className="fixed left-0 right-0 top-0 z-40 flex h-16 items-center border-b-2 border-divider bg-paper">
        <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-6 px-5 xl:px-6">
          <div className="flex shrink-0 items-center gap-3">
            {!isLoading && isAuthenticated && (
              <button
                type="button"
                onClick={() => setIsSidebarOpen((open) => !open)}
                aria-label="Toggle workspace sidebar"
                aria-controls="workspace-sidebar"
                aria-expanded={isSidebarOpen}
                className="hidden h-11 w-11 shrink-0 items-center justify-center bg-brand text-paper transition hover:bg-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand xl:flex"
              >
                {isSidebarOpen ? <X /> : <Menu />}
              </button>
            )}
            <Link
              href="/"
              className="text-[18px] font-extrabold tracking-[-0.015em] text-ink"
            >
              Quizwerk
            </Link>
          </div>

          <div className="hidden shrink-0 items-center gap-5 xl:flex">
            {visibleItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className={`whitespace-nowrap text-[15px] transition ${
                  isActive(item.href)
                    ? "font-extrabold text-brand"
                    : "text-ink hover:text-brand"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div className="hidden min-w-0 items-center gap-3 xl:flex">
            <NavGenerateQuizButton />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <>
                    <NotificationBell />
                    <OrganizationSwitcher className="shrink-0" />
                    <span
                      className="min-w-0 max-w-[144px] truncate text-[14px] text-ink"
                      title={`Hi, ${user?.username || "User"}${personaDefinition ? ` · ${personaDefinition.label}` : ""}`}
                    >
                      Hi, {user?.username || "User"}
                      {personaDefinition ? (
                        <span className="ml-[6px] text-[13px] text-ink/60">
                          · {personaDefinition.label}
                        </span>
                      ) : null}
                    </span>
                    <button onClick={logout} className={`${BTN_PRIMARY} shrink-0`}>
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
            type="button"
            onClick={() => setIsMobileNavOpen(!isMobileNavOpen)}
            className="flex h-11 w-11 shrink-0 items-center justify-center text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand xl:hidden"
            aria-label="Toggle mobile top-nav"
            aria-controls="compact-navigation"
            aria-expanded={isMobileNavOpen}
          >
            {isMobileNavOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      <div className="h-16" />

      {isMobileNavOpen && <div
        id="compact-navigation"
        className="fixed left-0 top-16 z-30 max-h-[calc(100dvh-64px)] w-full overflow-y-auto overscroll-contain border-b-2 border-divider bg-paper xl:hidden"
      >
        <div className="flex flex-col px-4 py-4">
          {visibleItems.map((item) => (
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
          ))}

          {!isLoading && isAuthenticated && (
            <>
              <p className="mb-1 mt-4 px-3 text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
                Workspace
              </p>
              {workspaceLinks.map((link) => (
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
                    <OrganizationSwitcher className="self-center" />
                    <span className="break-words text-center text-[15px] text-ink">
                      Hi, {user?.username || "User"}
                    </span>
                    <div className="flex justify-center">
                      <NotificationBell />
                    </div>
                    <UpgradePlanButton />
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
      </div>}

      <SignUpModal
        isOpen={isSignUpOpen}
        onClose={() => setIsSignUpOpen(false)}
        switchToSignIn={switchToSignIn}
      />
      <SignInModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        redirectTo={ROUTES.DASHBOARD}
        switchToSignUp={switchToSignUp}
      />
    </div>
  );
};

export default NavBar;
