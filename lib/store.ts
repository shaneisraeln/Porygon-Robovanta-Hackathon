"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// The frontend holds no business data — only which company we're viewing.
// Everything else is fetched from the backend on demand.
interface State {
  companyId: string | null;
  companyName: string | null;
  hydrated: boolean;
  setCompany: (id: string, name: string) => void;
  reset: () => void;
  setHydrated: () => void;
}

export const useStore = create<State>()(
  persist(
    (set) => ({
      companyId: null,
      companyName: null,
      hydrated: false,
      setCompany: (id, name) => set({ companyId: id, companyName: name }),
      reset: () => set({ companyId: null, companyName: null }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "cbo-session",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ companyId: s.companyId, companyName: s.companyName }),
      onRehydrateStorage: () => (state) => state?.setHydrated(),
    }
  )
);
