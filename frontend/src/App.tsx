import { BrowserRouter, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import RequireAuth from "./components/RequireAuth";
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
