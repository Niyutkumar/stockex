/* Routes, and the gate that keeps signed-out visitors out of the app. */

import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Trade from "./pages/Trade";
import Transactions from "./pages/Transactions";
import Watchlist from "./pages/Watchlist";

function Loading() {
  return <div className="center"><p className="muted">Loading…</p></div>;
}

/** Nothing renders until the stored token has been checked, so a signed-in
 *  user never sees the login screen flash past on a refresh. */
function RequireAuth({ children }) {
  const { status } = useAuth();
  if (status === "loading") return <Loading />;
  if (status !== "authenticated") return <Navigate to="/login" replace />;
  return children;
}

function RedirectIfSignedIn({ children }) {
  const { status } = useAuth();
  if (status === "loading") return <Loading />;
  if (status === "authenticated") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<RedirectIfSignedIn><Login /></RedirectIfSignedIn>} />
      <Route path="/register" element={<RedirectIfSignedIn><Register /></RedirectIfSignedIn>} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="trade" element={<Trade />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="watchlist" element={<Watchlist />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
