// Navbar — stub.
// TODO(Frontend): real nav, active states, and hide on the login route.

import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav>
      <Link to="/dashboard">Dashboard</Link>{" "}
      <Link to="/wardrobe">Wardrobe</Link>{" "}
      <Link to="/upload">Upload</Link>{" "}
      <Link to="/swipe">Swipe</Link>
    </nav>
  );
}
