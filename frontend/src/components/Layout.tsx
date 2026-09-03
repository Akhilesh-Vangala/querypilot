import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api, UserMe } from "../api";

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserMe | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => undefined);
  }, []);

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    navigate("/login");
  }

  return (
    <>
      <nav className="nav">
        <span className="nav-brand">QueryPilot</span>
        <div className="nav-links">
          <Link to="/">Ask</Link>
          <Link to="/history">History</Link>
          <Link to="/schema">Schema</Link>
          {user?.role === "admin" ? <Link to="/eval">Eval</Link> : null}
        </div>
        <span className="user-meta">{user?.email}</span>
        <button className="secondary" onClick={logout}>
          Log out
        </button>
      </nav>
      <main className="layout">
        <Outlet />
      </main>
    </>
  );
}
