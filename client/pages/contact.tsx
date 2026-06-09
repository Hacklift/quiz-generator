import React from "react";
import NavBar from "../components/home/NavBar";
import Footer from "../components/home/Footer";

export default function Contact() {
  return (
    <div className="flex flex-col min-h-screen">
      <NavBar />
      <main className="flex-grow max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-3xl md:text-4xl font-bold text-[#0F2654] mb-2">Contact Us</h1>
        <p className="text-gray-500 mb-8">We'd love to hear from you</p>
        
        <div className="bg-gray-50 rounded-lg p-8 mb-8">
          <div className="space-y-4">
            <p className="text-lg text-gray-700">
              📧 Email: <a href="mailto:support@quizgen.com" className="text-[#0F2654] hover:underline">support@quizgen.com</a>
            </p>
            <p className="text-lg text-gray-700">
              ⏱️ Response time: Within 24-48 hours
            </p>
            <p className="text-lg text-gray-700">
              💬 Or reach out on social media
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}