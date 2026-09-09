import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Swipe from "./pages/Swipe";
import Upload from "./pages/Upload";
import Wardrobe from "./pages/Wardrobe";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/swipe" element={<Swipe />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/wardrobe" element={<Wardrobe />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;