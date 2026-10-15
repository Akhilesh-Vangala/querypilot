import { useEffect, useState } from "react";
import {
  NavLink,
  Outlet,
  useNavigate,
  useLocation,
  Link,
} from "react-router-dom";
import { api, UserMe, RuntimeConfig } from "../../lib/api";
export default function Layout() {
  const navigate = useNavigate(),
    location = useLocation();
  const [user, setUser] = useState<UserMe | null>(null);
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    api.me().then(setUser);
    api.config().then(setConfig);
  }, []);
  const links = [
    ["/", "Overview"],
    ["/new", "New investigation"],
    ["/compare", "Compare periods"],
    ["/history", "Investigations"],
    ["/metrics", "Metric catalog"],
    ["/schema", "Warehouse"],
    ["/settings", "Workspace"],
  ];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-mark">Q</span>QueryPilot
        </Link>
        <p className="sidebar-caption">ANALYTICS WORKSPACE</p>
        <nav>
          {links.map(([path, title]) => (
            <NavLink end={path === "/"} key={path} to={path}>
              {title}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/eval">Evaluation lab</NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <span className="status-dot" />
          Synthetic claims dataset<p>{user?.email}</p>
          <button
            className="secondary"
            onClick={async () => {
              await api.logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="workspace">
        <header className="workspace-header">
          <span>
            Workspace{" "}
            <span className="muted">
              /{" "}
              {location.pathname.startsWith("/runs")
                ? "Investigation"
                : links.find(([p]) => p === location.pathname)?.[1] ||
                  "Evaluation"}
            </span>
          </span>
          <span className="pill">
            {config?.public_demo ? "Interactive demo" : "Private workspace"}
          </span>
        </header>
        {config?.public_demo && (
          <div className="demo-note">
            Synthetic data · Guided baseline · Investigation history is saved in
            this browser session.
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
