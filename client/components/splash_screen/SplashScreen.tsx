"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import React from "react";

const SplashScreen: React.FC = () => {
  const [fadeOut, setFadeOut] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadeOut(true), 2000);
    const hideTimer = setTimeout(() => setIsVisible(false), 2500);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(hideTimer);
    };
  }, []);

  if (!isVisible) return null;

  return (
    <div
      className={`fixed inset-0 z-[9999] flex items-center justify-center bg-logoBg transition-opacity duration-500 ${
        fadeOut ? "opacity-0" : "opacity-100"
      }`}
    >
      <Image
        src="/images/logo.png"
        alt="HQUIZ Logo"
        width={340}
        height={340}
        className="
          animate-pulse-slow
          drop-shadow-[0_0_60px_rgba(0,255,255,0.9)]
          drop-shadow-[0_0_100px_rgba(0,255,255,0.7)]
          drop-shadow-[0_0_160px_rgba(0,255,255,0.5)]
          scale-110
        "
        priority
      />
    </div>
  );
};

export default SplashScreen;
