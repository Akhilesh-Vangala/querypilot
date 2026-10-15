import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, login, RuntimeConfig } from "../../lib/api";
export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [config, setConfig] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    api.config().then(setConfig);
  }, []);
  async function signIn(e: string, p: string) {
    setBusy(true);
    setError("");
    try {
      await login(e, p);
      await api.me();
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    void signIn(email, password);
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">Q</span>QueryPilot
        </div>
        <div className="eyebrow">ANALYTICAL QUESTIONS. EXECUTED EVIDENCE.</div>
        <h1>
          Clarity starts
          <br />
          with the right
          <br />
          question.
        </h1>
        <p>
          Explore claims and provider-network operations through a traceable
          analytical workflow.
        </p>
        <div className="login-footer">
          Read-only analysis · Reviewed metric definitions · Query provenance
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <div className="eyebrow">YOUR ANALYTICS WORKSPACE</div>
          <h2>Welcome to QueryPilot.</h2>
          <p className="muted">
            Sign in to inspect the sample investigations.
          </p>
          <p><a href="/uploads">Use your own CSV — no account required ↗</a></p>
          <form onSubmit={submit}>
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button disabled={busy}>
              {busy ? "Opening workspace…" : "Sign in ↗"}
            </button>
          </form>
          {config?.demo_accounts && (
            <div className="demo-buttons">
              <span className="eyebrow">EXPLORE SYNTHETIC DATA</span>
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void signIn(
                    "analyst@querypilot.example.com",
                    "analyst-password",
                  )
                }
              >
                Open analyst demo →
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void signIn("admin@querypilot.example.com", "admin-password")
                }
              >
                Open evaluation demo →
              </button>
              <p className="small-note">
                Guided baseline. No live model request or customer data.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
