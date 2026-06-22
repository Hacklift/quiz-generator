import React from "react";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";

export default function Privacy() {
  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />
      <main className="flex-grow max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-3xl md:text-4xl font-bold text-[#0F2654] mb-2">Privacy Policy</h1>
        <p className="text-gray-500 mb-8">Last updated: {new Date().toLocaleDateString()}</p>
        
        <div className="prose prose-gray max-w-none space-y-6">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Information We Collect</h2>
            <p className="text-gray-600">Email address, name, quiz content, usage patterns.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">How We Use Data</h2>
            <p className="text-gray-600">To provide quiz generation, improve the service, and communicate with you.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Data Sharing</h2>
            <p className="text-gray-600">We don't sell your data. AI providers may process quiz content for generation.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Your Rights</h2>
            <p className="text-gray-600">Access, delete, or export your data upon request.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Cookies</h2>
            <p className="text-gray-600">Used for authentication and analytics.</p>
          </section>
          
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact</h2>
            <p className="text-gray-600">Privacy questions: <a href="mailto:privacy@quizgen.com" className="text-[#0F2654] hover:underline">privacy@quizgen.com</a></p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}