"use client";

import React from "react";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
import { usePersona } from "@features/persona/context/personaContext";
import { archivo } from "@shared/ui/quizwerk";
import PersonaGate from "@features/dashboard/components/PersonaGate";
import SchoolDashboard from "@features/dashboard/school/SchoolDashboard";
import CorporateDashboard from "@features/dashboard/corporate/CorporateDashboard";

/**
 * [SCAFFOLD-OWNED] Persona dashboard root.
 *
 * Resolves the persona, then hands off to the category dashboard, which in
 * turn dispatches to the user-type view. Adding a category means adding a
 * branch here; adding a user type means editing that category's map.
 */
export default function DashboardPage() {
  const { user } = useAuth();
  const { persona, isLoading } = usePersona();

  return (
    <RequireAuth>
      <div className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}>
        <NavBar />
        <main className="flex-grow">
          {isLoading || !user ? (
            <div className="flex min-h-[40vh] items-center justify-center">
              <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" />
            </div>
          ) : !persona ? (
            <PersonaGate />
          ) : persona.category === "school" ? (
            <SchoolDashboard persona={persona} user={user} />
          ) : (
            <CorporateDashboard persona={persona} user={user} />
          )}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
