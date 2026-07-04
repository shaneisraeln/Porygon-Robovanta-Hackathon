"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStore } from "@/lib/store";

const links = [
  { href: "/", label: "Brief" },
  { href: "/brain", label: "Brain" },
  { href: "/sources", label: "Sources" },
  { href: "/council", label: "Council" },
  { href: "/investors", label: "Investors" },
  { href: "/fundraising", label: "Fundraising" },
];

export function TopNav() {
  const pathname = usePathname();
  const companyName = useStore((s) => s.companyName);
  const companyId = useStore((s) => s.companyId);

  if (pathname === "/onboarding") {
    return (
      <header className="px-5 py-4 sm:px-8">
        <Brand />
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-3 sm:px-8">
        <div className="flex items-center gap-3">
          <Brand />
          {companyName && (
            <span className="hidden text-sm text-faint sm:inline">
              <span className="text-muted">/</span> {companyName}
            </span>
          )}
        </div>

        {companyId && (
          <nav className="flex items-center gap-0.5">
            {links.map((l) => {
              const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                    active ? "font-medium text-ink" : "text-muted hover:text-ink"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        )}
      </div>
    </header>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span className="grid h-7 w-7 place-items-center rounded-lg bg-ink">
        <span className="h-2 w-2 animate-breathe rounded-full bg-accent" />
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-ink">CBO</span>
    </Link>
  );
}
