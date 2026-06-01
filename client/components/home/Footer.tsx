"use client";

import React from "react";
import Link from "next/link";
import { FaGithub, FaTwitter, FaLinkedin } from "react-icons/fa";

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 py-12 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Column */}
          <div className="col-span-1 md:col-span-1">
            <h3 className="text-xl font-bold text-[#0F2654] mb-4">QuizGen</h3>
            <p className="text-sm text-gray-500">
              Generate AI-powered quizzes instantly.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li><Link href="/generate" className="hover:text-[#0F2654]">Generate Quiz</Link></li>
              <li><Link href="/pricing" className="hover:text-[#0F2654]">Pricing</Link></li>
              <li><Link href="/features" className="hover:text-[#0F2654]">Features</Link></li>
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Company</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li><Link href="/company" className="hover:text-[#0F2654]">About</Link></li>
              <li><Link href="/contact" className="hover:text-[#0F2654]">Contact</Link></li>
              <li><Link href="/terms" className="hover:text-[#0F2654]">Terms</Link></li>
              <li><Link href="/privacy" className="hover:text-[#0F2654]">Privacy</Link></li>
            </ul>
          </div>

          {/* Social */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Follow Us</h4>
            <div className="flex space-x-4">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-[#0F2654]">
                <FaGithub size={20} />
              </a>
              <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-[#0F2654]">
                <FaTwitter size={20} />
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-[#0F2654]">
                <FaLinkedin size={20} />
              </a>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 mt-8 pt-8 text-center text-sm text-gray-400">
          <p>© {new Date().getFullYear()} QuizGen. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}