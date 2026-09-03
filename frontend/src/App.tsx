import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Ask from "./pages/Ask";
import EvalPage from "./pages/EvalPage";
import History from "./pages/History";
import Login from "./pages/Login";
import Schema from "./pages/Schema";

function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
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
          <Route index element={<Ask />} />
          <Route path="history" element={<History />} />
          <Route path="schema" element={<Schema />} />
          <Route path="eval" element={<EvalPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
