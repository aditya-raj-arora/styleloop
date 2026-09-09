// Navbar — stub.
// TODO(Frontend): active states, real styling.

import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../store/useAuth";

export default function Navbar() {
  const token = useAuth((state) => state.token);
  const clear = useAuth((state) => state.clear);
  const navigate = useNavigate();

  if (!token) {
    // Logged out: nothing to navigate to yet, just the login/signup page.
    return null;
  }

  function handleLogout() {
    clear();
    navigate("/", { replace: true });
  }

  return (
    <nav>
      <Link to="/dashboard">Dashboard</Link>{" "}
      <Link to="/wardrobe">Wardrobe</Link>{" "}
      <Link to="/upload">Upload</Link>{" "}
      <Link to="/swipe">Swipe</Link>{" "}
      <button type="button" onClick={handleLogout}>
        Log out
      </button>
    </nav>
  );
}
