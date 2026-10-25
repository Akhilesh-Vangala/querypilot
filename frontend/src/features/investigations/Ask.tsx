import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, RuntimeConfig } from "../../lib/api";
import StudioIcon from "../../components/layout/StudioIcon";
import { STARTERS } from "./questions";

export default function Ask() {
  const navigate = useNavigate(),
    [params] = useSearchParams();
  const [question, setQuestion] = useState(() =>
    (params.get("question") || "Claims paid by specialty").slice(0, 4000),
  );
  const [mode, setMode] = useState("baseline"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [config, setConfig] = useState<RuntimeConfig | null>(null),
    [configError, setConfigError] = useState(false);
  const reference = params.get("reference") || "";
  const safeReference = /^[a-zA-Z0-9_-]{1,128}$/.test(reference)
    ? reference
    : "";
  function loadConfig() {
    setConfigError(false);
    api
      .config()
      .then(setConfig)
      .catch(() => setConfigError(true));
  }
  useEffect(loadConfig, []);
  useEffect(() => {
    setQuestion(
      (params.get("question") || "Claims paid by specialty").slice(0, 4000),
    );
  }, [params]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !question.trim() || !config) return;
    setBusy(true);
    setError("");
    try {
      const run = await api.createAnalysis(question.trim(), mode);
      navigate("/runs/" + run.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Investigation failed");
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading agent-question-heading">
        <Link className="back-link" to="/demo">
          ← Investigation desk
        </Link>
        <div className="eyebrow">QUESTION → PLAN → TOOLS → EVIDENCE</div>
        <h1>Start an investigation.</h1>
        <p>
          Give the investigator a precise question. Keep its execution,
          assumptions and verification in view.
        </p>
      </div>
      <div className="agent-compose-layout">
        <section className="card agent-question-card">
          <div className="agent-card-heading">
            <span className="agent-orbit" aria-hidden="true">
              <StudioIcon name="query" />
            </span>
            <div>
              <span className="eyebrow">INVESTIGATION BRIEF</span>
              <h2>Your analytical question</h2>
            </div>
            <span className="pill">
              {mode === "live" ? "Live model" : "Guided baseline"}
            </span>
          </div>
          {safeReference && (
            <p className="agent-reference">
              New investigation referencing{" "}
              <Link to={"/runs/" + safeReference}>
                {safeReference.slice(0, 8)} ↗
              </Link>
              . Previous results are not automatically added to model context.
            </p>
          )}
          <form onSubmit={submit}>
            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              rows={5}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
              maxLength={4000}
              placeholder="Describe the metric, period and breakdown you want to investigate…"
              onKeyDown={(e) => {
                if (
                  (e.metaKey || e.ctrlKey) &&
                  e.key === "Enter" &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="agent-question-hints">
              <span>Include a metric, time window and grouping.</span>
              <span>{question.length.toLocaleString()} / 4,000</span>
            </div>
            <div
              className="agent-prompt-options"
              aria-label="Reviewed question starters"
            >
              {STARTERS.map((s) => (
                <button
                  type="button"
                  className="secondary"
                  key={s.label}
                  onClick={() => setQuestion(s.question)}
                  disabled={busy}
                >
                  <StudioIcon name={s.icon} />
                  {s.label}
                </button>
              ))}
            </div>
            <div className="agent-mode-field">
              <div>
                <label htmlFor="mode">Investigator</label>
                <select
                  id="mode"
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  disabled={busy}
                >
                  <option value="baseline">Guided development baseline</option>
                  <option value="live" disabled={!config?.live_available}>
                    Live model investigator
                    {!config?.live_available ? " · not configured" : ""}
                  </option>
                </select>
              </div>
              <p>
                {mode === "live"
                  ? "Uses the configured model and records reported token usage."
                  : "Deterministic investigator over reviewed synthetic questions. No provider calls."}
              </p>
            </div>
            {configError && (
              <div className="error" role="alert">
                Execution limits could not be loaded.{" "}
                <button
                  type="button"
                  className="secondary"
                  onClick={loadConfig}
                >
                  Retry configuration
                </button>
              </div>
            )}
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="agent-submit-row">
              <span>
                <StudioIcon name="data" /> Synthetic claims warehouse
              </span>
              <button disabled={busy || !question.trim() || !config}>
                {busy ? "Creating investigation…" : "Investigate question ↗"}
              </button>
              <span className="agent-keyhint">⌘ / Ctrl + Enter</span>
            </div>
          </form>
        </section>
        <aside className="agent-policy-panel">
          <div className="agent-policy-title">
            <StudioIcon name="settings" />
            <h2>Execution contract</h2>
          </div>
          <p>
            Application-enforced limits, independent of the investigator’s
            proposal.
          </p>
          <dl>
            {[
              ["Model rounds", config?.max_rounds],
              ["SQL executions", config?.max_sql_attempts],
              ["Returned rows", config?.max_rows],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt>{label}</dt>
                <dd>{value ?? "Loading…"}</dd>
              </div>
            ))}
          </dl>
          <ol className="agent-policy-flow">
            {[
              ["Scope", "Reviewed metrics and authorized relations"],
              ["Execute", "Typed actions and read-only SQL policy"],
              ["Check", "Reviewed comparison checks; scoped query receipts"],
              ["Publish", "Inspectable result, SQL and provenance"],
            ].map(([title, detail], i) => (
              <li key={title}>
                <span>{i + 1}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{detail}</p>
                </div>
              </li>
            ))}
          </ol>
          <Link to="/metrics">Review the metric catalog →</Link>
          <Link to="/compare">Define a period comparison →</Link>
        </aside>
      </div>
    </>
  );
}
