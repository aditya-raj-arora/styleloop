import { Heart, Home, Luggage, LogOut, Shirt, Upload } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../store/useAuth";

const _LINKS = [
  { to: "/dashboard", label: "Dashboard", Icon: Home },
  { to: "/wardrobe", label: "Wardrobe", Icon: Shirt },
  { to: "/swipe", label: "Swipe outfits", Icon: Heart },
  { to: "/upload", label: "Upload garment", Icon: Upload },
  { to: "/packing", label: "Pack for a trip", Icon: Luggage },
] as const;

const _ICON_LINK_CLASS =
  "p-1 rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-400";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const clear = useAuth((state) => state.clear);

  function handleLogout() {
    clear();
    navigate("/", { replace: true });
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 flex justify-around py-3 bg-zinc-900 border-t border-zinc-800">
      {_LINKS.map(({ to, label, Icon }) => (
        <Link
          key={to}
          to={to}
          aria-label={label}
          aria-current={location.pathname === to ? "page" : undefined}
          className={`${_ICON_LINK_CLASS} ${
            location.pathname === to ? "text-amber-400" : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Icon />
        </Link>
      ))}

      <button
        type="button"
        onClick={handleLogout}
        aria-label="Log out"
        className={`${_ICON_LINK_CLASS} text-gray-400 hover:text-gray-200`}
      >
        <LogOut />
      </button>
    </nav>
  );
}
