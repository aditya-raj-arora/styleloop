import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Swipe from "./pages/Swipe";
import Upload from "./pages/Upload";
import Wardrobe from "./pages/Wardrobe";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/wardrobe" element={<Wardrobe />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/swipe" element={<Swipe />} />
      </Routes>
    </BrowserRouter>
  );
}
