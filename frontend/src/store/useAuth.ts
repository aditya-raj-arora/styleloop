// In-memory auth token store (Zustand).
//
// Intentionally NOT persisted to localStorage — the JWT lives only for the tab
// session. A refresh clears it and the user re-authenticates.

import { create } from "zustand";

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
  clear: () => set({ token: null }),
}));
