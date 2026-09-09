import { Home, LogOut, Shirt, Upload } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../store/useAuth";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const clear = useAuth((state) => state.clear);

  function handleLogout() {
    clear();
    navigate("/", { replace: true });
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 flex justify-around py-3 bg-zinc-900 border-t">
      <Link
        to="/dashboard"
        className={
          location.pathname === "/dashboard"
            ? "text-amber-400"
            : "text-gray-400"
        }
      >
        <Home />
      </Link>

      <Link
        to="/wardrobe"
        className={
          location.pathname === "/wardrobe"
            ? "text-amber-400"
            : "text-gray-400"
        }
      >
        <Shirt />
      </Link>

      <Link
        to="/upload"
        className={
          location.pathname === "/upload"
            ? "text-amber-400"
            : "text-gray-400"
        }
      >
        <Upload />
      </Link>

      <button type="button" onClick={handleLogout} className="text-gray-400">
        <LogOut />
      </button>
    </nav>
  );
}