import { BrowserRouter, Routes, Route } from "react-router-dom";

import RequireAuth from "./components/RequireAuth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import SharedOutfit from "./pages/SharedOutfit";
import Swipe from "./pages/Swipe";
import Upload from "./pages/Upload";
import Wardrobe from "./pages/Wardrobe";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        {/* Public — no RequireAuth: the share token itself is the credential. */}
        <Route path="/shared/:token" element={<SharedOutfit />} />
        <Route
          path="/wardrobe"
          element={
            <RequireAuth>
              <Wardrobe />
            </RequireAuth>
          }
        />
        <Route
          path="/upload"
          element={
            <RequireAuth>
              <Upload />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/swipe"
          element={
            <RequireAuth>
              <Swipe />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;