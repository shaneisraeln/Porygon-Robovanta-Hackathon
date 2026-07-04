"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useStore } from "@/lib/store";

/** Gates the app behind onboarding. Renders nothing until the session has
 *  rehydrated, then routes to onboarding if no company is selected. */
export function RequireCompany({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hydrated = useStore((s) => s.hydrated);
  const companyId = useStore((s) => s.companyId);

  useEffect(() => {
    if (hydrated && !companyId) router.replace("/onboarding");
  }, [hydrated, companyId, router]);

  if (!hydrated) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <div className="h-2 w-2 animate-breathe rounded-full bg-accent" />
      </div>
    );
  }
  if (!companyId) return null;
  return <>{children}</>;
}
