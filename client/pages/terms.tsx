import React from "react";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";

export default function Terms() {
  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />
      <main className="flex-grow max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-3xl md:text-4xl font-bold text-[#0F2654] mb-2">Terms of Service</h1>
        <p className="text-gray-500 mb-8">Last updated: {new Date().toLocaleDateString()}</p>
        
        <div className="prose prose-gray max-w-none space-y-6">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">1. Acceptance of Terms</h2>
            <p className="text-gray-600">By accessing QuizGen, you agree to these terms.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">2. User Accounts</h2>
            <p className="text-gray-600">You are responsible for maintaining your account security.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">3. Content Ownership</h2>
            <p className="text-gray-600">You retain rights to quizzes you create. QuizGen may use anonymized data to improve services.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">4. Prohibited Use</h2>
            <p className="text-gray-600">Do not misuse the service for illegal activities or spam.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">5. Termination</h2>
            <p className="text-gray-600">We may suspend accounts violating these terms.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">6. Contact</h2>
            <p className="text-gray-600">Questions? Email us at <a href="mailto:legal@quizgen.com" className="text-[#0F2654] hover:underline">legal@quizgen.com</a></p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}