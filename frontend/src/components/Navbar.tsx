import { Home, Shirt, Upload } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

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
    </nav>
  );
}