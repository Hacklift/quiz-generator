import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: "#050F34",
        logoBg: "#030B1F",
        // Quizwerk redesign tokens (design_handoff_home_page)
        paper: "#f3f2f2",
        ink: "#201e1d",
        divider: "rgba(32, 30, 29, 0.4)",
        brand: {
          DEFAULT: "#0a3264",
          100: "#e7ecf3",
          200: "#cdd8e6",
          300: "#a5b7d0",
          400: "#476490",
          600: "#082a54",
          700: "#062042",
          800: "#041730",
          900: "#030f20",
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseScale: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.05)" },
        },
        livePulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.2" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.8s ease-out forwards",
        "pulse-slow": "pulseScale 2s ease-in-out infinite",
        "live-pulse": "livePulse 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
