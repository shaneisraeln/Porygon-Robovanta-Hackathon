import type { Metadata } from "next";
import "./globals.css";
import { TopNav } from "@/components/TopNav";

export const metadata: Metadata = {
  title: "CBO — your AI Chief Business Officer",
  description:
    "CBO runs the business with you. It works overnight, analyzes, prioritizes, and prepares — so you only make decisions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      {/* suppressHydrationWarning: browser extensions inject body attributes
          before React hydrates; those mismatches are harmless and out of our control. */}
      <body suppressHydrationWarning className="min-h-screen bg-canvas font-sans text-ink antialiased">
        <TopNav />
        {children}
      </body>
    </html>
  );
}
