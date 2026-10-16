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
import {
  Home,
  RunDetail,
  Metrics,
  SettingsPage,
} from "../features/workbench/Workbench";
import { api } from "../lib/api";
import ProductApp from "../features/product/ProductApp";
import { ProductProvider } from "../features/product/context";
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
      <ProductProvider>
        <Routes>
          <Route path="/" element={<ProductApp />} />
          <Route path="/uploads" element={<ProductApp />} />
          <Route
            path="/uploads/index.html"
            element={<Navigate to="/uploads" replace />}
          />
          <Route path="/workspace/*" element={<ProductApp />} />
          <Route
            path="/login"
            element={
              <div className="legacy-root">
                <Login />
              </div>
            }
          />
          <Route
            element={
              <div className="legacy-root">
                <PrivateRoute>
                  <Layout />
                </PrivateRoute>
              </div>
            }
          >
            <Route path="/demo" element={<Home />} />
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
      </ProductProvider>
    </BrowserRouter>
  );
}
