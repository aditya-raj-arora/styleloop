// Persisted auth token store (Zustand + localStorage).
//
// The JWT is persisted to localStorage so a page refresh (or closing and
// reopening the tab) doesn't log the user out. Trade-off: a token sitting in
// localStorage is readable by any script running on the page, so an XSS bug
// elsewhere in the app could exfiltrate it — the same risk most SPA
// client-side auth schemes carry without a backend session/httpOnly-cookie
// layer. Acceptable here; revisit if that threat model changes.

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
      clear: () => set({ token: null }),
    }),
    { name: "styleloop-auth" },
  ),
);
