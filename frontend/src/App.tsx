import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import Layout from "./components/Layout";
import Ask from "./pages/Ask";
import EvalPage from "./pages/EvalPage";
import History from "./pages/History";
import Login from "./pages/Login";
import Schema from "./pages/Schema";
import { Home, RunDetail, Metrics, SettingsPage } from "./pages/Workbench";
import { api } from "./api";
function PrivateRoute({ children }: { children: JSX.Element }) {
  const [state, setState] = useState<"loading" | "ready" | "login">("loading");
  const location = useLocation();
  useEffect(() => {
    let active = true;
    api
      .config()
      .then(() => api.me())
      .then(() => {
        if (active) setState("ready");
      })
      .catch(() => {
        if (active) setState("login");
      });
    return () => {
      active = false;
    };
  }, [location.pathname]);
  if (state === "loading")
    return <div className="loading-page">Opening your workspace…</div>;
  return state === "ready" ? children : <Navigate to="/login" replace />;
}
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Home />} />
          <Route path="new" element={<Ask />} />
          <Route path="runs/:id" element={<RunDetail />} />
          <Route path="history" element={<History />} />
          <Route path="schema" element={<Schema />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="eval" element={<EvalPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
