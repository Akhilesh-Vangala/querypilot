import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, RuntimeConfig } from "../api";
const EXAMPLES = [
  "Claims paid by specialty",
  "Declined referral rate by specialty",
  "Which region had the most referrals?",
  "What is total claims paid last 12 months?",
  "Which employer groups had any closed panel weeks?",
  "Average care coordination cost per case by region and employer",
];
export default function Ask() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("Claims paid by specialty"),
    [mode, setMode] = useState("baseline"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [config, setConfig] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    api.config().then(setConfig);
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const run = await api.createAnalysis(question, mode);
      navigate("/runs/" + run.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Investigation failed");
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <Link className="back-link" to="/">
          ← Overview
        </Link>
        <div className="eyebrow">QUESTION TO EVIDENCE</div>
        <h1>Start an investigation.</h1>
        <p>
          Define the metric and scope. Inspect the query and its evidence before
          using the answer.
        </p>
      </div>
      <div className="two-columns">
        <section className="card">
          <h2>Your analytical question</h2>
          <form onSubmit={submit}>
            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              rows={6}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
              maxLength={4000}
            />
            <div className="form-grid">
              <div>
                <label htmlFor="mode">Investigator</label>
                <select
                  id="mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                >
                  <option value="baseline">Guided development baseline</option>
                  <option value="live" disabled={!config?.live_available}>
                    Live model investigator
                    {!config?.live_available ? " · not configured" : ""}
                  </option>
                </select>
              </div>
              <div className="small-note">
                Read-only queries
                <br />
                Up to {config?.max_rows || 500} returned rows
              </div>
            </div>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="form-actions">
              <button disabled={busy}>
                {busy ? "Creating investigation…" : "Investigate question ↗"}
              </button>
            </div>
          </form>
        </section>
        <aside>
          <div className="card">
            <div className="eyebrow">START WITH A KNOWN METRIC</div>
            <h2>Questions to explore</h2>
            <div className="example-list">
              {EXAMPLES.map((q) => (
                <button
                  className="example"
                  key={q}
                  onClick={() => setQuestion(q)}
                >
                  {q}
                  <span>↗</span>
                </button>
              ))}
            </div>
          </div>
          <div className="card muted">
            <h3>Useful scope</h3>
            <p>
              Include the time window, grouping and denominator. Separate
              metrics have different grains; combining them requires a
              deliberate join.
            </p>
            <Link to="/metrics">Review metric definitions →</Link>
          </div>
        </aside>
      </div>
    </>
  );
}
