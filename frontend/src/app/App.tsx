import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import Layout from "../components/layout/Layout";
import Ask from "../features/investigations/Ask";
import Compare from "../features/comparisons/Compare";
import EvalPage from "../features/evaluation/EvalPage";
import History from "../features/history/History";
import Login from "../features/auth/Login";
import Schema from "../features/catalog/Schema";
import { Home, RunDetail, Metrics, SettingsPage } from "../features/workbench/Workbench";
import { api } from "../lib/api";
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
function UploadWorkspace() {
  useEffect(() => { window.location.replace("/uploads/index.html"); }, []);
  return <div className="loading-page">Opening your data workspace…</div>;
}
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/uploads" element={<UploadWorkspace />} />
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
          <Route path="compare" element={<Compare />} />
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
