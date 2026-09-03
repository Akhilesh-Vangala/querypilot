import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, login } from "../api";

const DEMO_ACCOUNTS = [
  { label: "Analyst demo", email: "analyst@querypilot.example.com", password: "analyst-password" },
  { label: "Admin demo", email: "admin@querypilot.example.com", password: "admin-password" },
];

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function finish(token: string) {
    localStorage.setItem("token", token);
    const me = await api.me();
    localStorage.setItem("role", me.role);
    navigate("/");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await finish(await login(email, password));
    } catch {
      setError("Invalid email or password.");
    }
  }

  async function demoLogin(demoEmail: string, demoPassword: string) {
    setError("");
    try {
      await finish(await login(demoEmail, demoPassword));
    } catch {
      setError("Demo login failed. Is the API running?");
    }
  }

  return (
    <div className="login-page">
      <div className="card login-card">
        <h1>QueryPilot</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Natural-language analytics over a lens-manufacturing warehouse
        </p>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" style={{ width: "100%" }}>
            Sign in
          </button>
        </form>
        <div className="demo-buttons">
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Demo accounts
          </span>
          {DEMO_ACCOUNTS.map((acct) => (
            <button key={acct.email} type="button" className="secondary" onClick={() => demoLogin(acct.email, acct.password)}>
              {acct.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
