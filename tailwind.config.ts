import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#16161a", // primary text
        muted: "#6b6b76", // secondary text
        faint: "#9b9ba6", // tertiary text
        line: "#ececef", // hairlines
        surface: "#ffffff",
        canvas: "#fafaf8", // warm paper background
        accent: "#5b54e8", // single restrained accent
        good: "#1a8f5c",
        warn: "#b7791f",
        danger: "#d1453b",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      maxWidth: { reading: "44rem" },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "fade": { from: { opacity: "0" }, to: { opacity: "1" } },
        breathe: { "0%,100%": { opacity: "0.5" }, "50%": { opacity: "1" } },
        drift: { from: { transform: "rotate(0deg)" }, to: { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16,1,0.3,1) both",
        fade: "fade 0.4s ease-out both",
        breathe: "breathe 3s ease-in-out infinite",
        drift: "drift 120s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
