// Redirects to the login route ("/") when there's no JWT in useAuth.
//
// Wrap any route element that needs an authenticated user:
//   <Route path="/wardrobe" element={<RequireAuth><Wardrobe /></RequireAuth>} />

import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../store/useAuth";

export default function RequireAuth({ children }: { children: ReactElement }) {
  const token = useAuth((state) => state.token);
  const location = useLocation();

  if (!token) {
    // Remember where the user was headed so Login can send them back after auth.
    return <Navigate to="/" replace state={{ from: location }} />;
  }

  return children;
}
