import { useEffect, useState, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Run, Metric, RuntimeConfig } from "../api";
import BarChart from "../components/BarChart";
export function Home() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    api
      .config()
      .then(setConfig)
      .then(() => api.analyses())
      .then(setRuns);
  }, []);
  return (
    <>
      <div className="page-heading home-heading">
        <div>
          <div className="eyebrow">CLAIMS + PROVIDER NETWORK</div>
          <h1>
            Ask a better question.
            <br />
            Inspect a better answer.
          </h1>
          <p>
            Evidence-backed analytics across claims, referrals, network capacity
            and coordination.
          </p>
        </div>
        <Link className="button" to="/new">
          New investigation ↗
        </Link>
      </div>
      <div className="stats">
        <div>
          <span>Investigations</span>
          <strong>{runs.length.toString().padStart(2, "0")}</strong>
        </div>
        <div>
          <span>Reviewed metrics</span>
          <strong>05</strong>
        </div>
        <div>
          <span>Authorized relations</span>
          <strong>08</strong>
        </div>
        <div>
          <span>Investigator</span>
          <strong className="text-value">
            {config?.live_available ? "AI available" : "Guided baseline"}
          </strong>
        </div>
      </div>
      <div className="two-columns">
        <section className="card">
          <div className="section-heading">
            <h2>Recent investigations</h2>
            <Link to="/history">View all →</Link>
          </div>
          {runs.length ? (
            runs.slice(0, 5).map((r) => (
              <Link className="run-row" to={"/runs/" + r.id} key={r.id}>
                <div>
                  <strong>{r.question}</strong>
                  <small>{new Date(r.created_at).toLocaleString()}</small>
                </div>
                <span className="pill">{r.status.replaceAll("_", " ")}</span>
              </Link>
            ))
          ) : (
            <div className="empty-state">
              <span>↗</span>
              <h3>Your next question starts here.</h3>
              <p>
                Investigate a metric, inspect its plan, and keep the executed
                query with the result.
              </p>
              <Link to="/new">Start an investigation →</Link>
            </div>
          )}
        </section>
        <section>
          <div className="card feature-card">
            <div className="eyebrow">A TRACEABLE ANALYTICAL WORKFLOW</div>
            <h2>From intent to a checked result.</h2>
            <ol className="flow-list">
              <li>
                <span>01</span>
                <div>
                  <strong>Scope</strong>
                  <p>Reviewed definitions, dimensions and metric grain.</p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <strong>Investigate</strong>
                  <p>Bounded tools and a public query plan.</p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <strong>Execute</strong>
                  <p>Read-only query policy and database controls.</p>
                </div>
              </li>
              <li>
                <span>04</span>
                <div>
                  <strong>Inspect</strong>
                  <p>Results, completeness and execution provenance.</p>
                </div>
              </li>
            </ol>
          </div>
          <div className="card">
            <h3>Know what the result establishes.</h3>
            <p className="muted">
              Query execution and policy checks are distinct from proving a
              business interpretation. Review assumptions alongside the data.
            </p>
            <Link to="/metrics">Explore the semantic catalog →</Link>
          </div>
        </section>
      </div>
    </>
  );
}
export function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState<Run | null>(null),
    [error, setError] = useState("");
  const [tab, setTab] = useState("result");
  const [drawer, setDrawer] = useState(false);
  const drawerLauncher = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    async function poll() {
      try {
        const r = await api.analysis(id!);
        if (!active) return;
        setRun(r);
        if (["queued", "running"].includes(r.status))
          timer = window.setTimeout(poll, 1000);
      } catch (e) {
        if (active)
          setError(
            e instanceof Error ? e.message : "Unable to load investigation",
          );
      }
    }
    void poll();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [id]);
  if (error)
    return (
      <div className="card">
        <Link to="/history">← Investigations</Link>
        <p role="alert">{error}</p>
      </div>
    );
  if (!run) return <div className="loading-page">Loading investigation…</div>;
  const result = run.result;
  const events = result?.events || run.events || [];
  return (
    <>
      <div className="page-heading">
        <Link className="back-link" to="/history">
          ← Investigations
        </Link>
        <div className="section-heading">
          <div>
            <div className="eyebrow">INVESTIGATION / {run.id.slice(0, 8)}</div>
            <h1>{run.question}</h1>
          </div>
          <span className="pill">{run.status.replaceAll("_", " ")}</span>
        </div>
        <p>
          {result?.model_mode || run.mode} · Synthetic claims warehouse ·{" "}
          {new Date(run.created_at).toLocaleString()}
        </p>
      </div>
      <div className="run-layout">
        <section>
          {!result ? (
            <div className="card">
              <h2>
                {["queued", "running"].includes(run.status)
                  ? "Investigation in progress"
                  : "Investigation stopped"}
              </h2>
              <p>
                {run.error_kind
                  ? "The run did not publish an answer. Retained events identify its last completed stage."
                  : "The worker will publish the plan, query and result here."}
              </p>
            </div>
          ) : (
            <>
              <div className="stats compact">
                <div>
                  <span>Model rounds</span>
                  <strong>{result.rounds}</strong>
                </div>
                <div>
                  <span>SQL attempts</span>
                  <strong>{result.attempts}</strong>
                </div>
                <div>
                  <span>Returned rows</span>
                  <strong>{result.rows.length}</strong>
                </div>
                <div>
                  <span>Elapsed</span>
                  <strong>{(result.elapsed_ms / 1000).toFixed(1)}s</strong>
                </div>
              </div>
              <div className="tabs">
                {["result", "query", "plan"].map((t) => (
                  <button
                    key={t}
                    className={tab === t ? "active" : ""}
                    onClick={() => setTab(t)}
                  >
                    {t === "query"
                      ? "Executed SQL"
                      : t === "plan"
                        ? "Plan + assumptions"
                        : "Result"}
                  </button>
                ))}
              </div>
              <div className="card result-card">
                {tab === "result" ? (
                  <>
                    <div className="eyebrow">
                      {result.refused
                        ? "POLICY REFUSAL"
                        : result.status === "needs_clarification"
                          ? "CLARIFICATION NEEDED"
                          : "EXECUTED RESULT"}
                    </div>
                    <h2>{result.answer}</h2>
                    {result.validation?.possibly_truncated && (
                      <div className="callout">
                        The result reached the row limit. Treat this view as
                        potentially incomplete; narrow or aggregate the query.
                      </div>
                    )}
                    {result.chart === "bar" && result.rows.length > 0 && (
                      <BarChart columns={result.columns} rows={result.rows} />
                    )}
                    {result.columns.length > 0 && (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              {result.columns.map((c) => (
                                <th key={c}>{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {result.rows.map((row, i) => (
                              <tr key={i}>
                                {row.map((v, j) => (
                                  <td key={j}>
                                    {v == null
                                      ? "—"
                                      : typeof v === "number"
                                        ? v.toLocaleString(undefined, {
                                            maximumFractionDigits: 4,
                                          })
                                        : String(v)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                ) : tab === "query" ? (
                  <>
                    <div className="section-heading">
                      <h2>Executed read-only SQL</h2>
                      <button
                        className="secondary"
                        onClick={() =>
                          navigator.clipboard.writeText(result.sql)
                        }
                      >
                        Copy SQL
                      </button>
                    </div>
                    <pre>{result.sql || "No query was executed."}</pre>
                    <p className="muted">
                      Relation/function scopes, read-only execution and output
                      budgets were checked before publication.
                    </p>
                  </>
                ) : (
                  <>
                    <h2>
                      {result.plan?.objective ||
                        "No executable plan was published."}
                    </h2>
                    <h3>Assumptions</h3>
                    <ul>
                      {result.plan?.assumptions.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                    <h3>Declared checks</h3>
                    <ul>
                      {result.plan?.checks.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                    <p className="muted">
                      These are public analysis statements, not hidden model
                      reasoning.
                    </p>
                  </>
                )}
              </div>
              {result.validation && (
                <div className="card">
                  <div className="section-heading">
                    <div>
                      <div className="eyebrow">PROVENANCE</div>
                      <h3>Execution checks are retained.</h3>
                    </div>
                    <button
                      className="secondary"
                      ref={drawerLauncher}
                      onClick={() => setDrawer(true)}
                    >
                      Inspect record
                    </button>
                  </div>
                  <p className="muted">
                    {result.validation.semantic_guarantee}
                  </p>
                </div>
              )}
            </>
          )}
        </section>
        <aside className="card activity-card">
          <div className="eyebrow">PUBLIC WORKFLOW EVENTS</div>
          <h2>Investigation activity</h2>
          <ol className="timeline">
            {events.map((e, i) => (
              <li key={i}>
                <strong>{e.stage.replaceAll("_", " ")}</strong>
                <small>
                  {e.tool || e.status} · {(e.elapsed_ms / 1000).toFixed(1)}s
                </small>
              </li>
            ))}
          </ol>
        </aside>
      </div>
      {drawer && (
        <ProvenanceDrawer
          result={result}
          returnFocus={drawerLauncher.current}
          close={() => setDrawer(false)}
        />
      )}
    </>
  );
}
export function Metrics() {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  useEffect(() => {
    api.metrics().then((r) => setMetrics(r.metrics));
  }, []);
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">REVIEWED SEMANTIC CONTRACTS</div>
        <h1>Start with a definition.</h1>
        <p>Units, denominators and data grain travel with the query.</p>
      </div>
      <div className="metric-grid">
        {metrics.map((m) => (
          <article className="card" key={m.id}>
            <div className="section-heading">
              <h2>{m.name}</h2>
              <span className="pill">{m.unit}</span>
            </div>
            <p className="muted">{m.definition}</p>
            <div className="metric-meta">
              <span>Grain</span>
              <strong>{m.grain}</strong>
              <span>Source</span>
              <strong>{m.table}</strong>
            </div>
            <pre>{m.expression}</pre>
          </article>
        ))}
      </div>
    </>
  );
}
export function SettingsPage() {
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  useEffect(() => {
    api.config().then(setConfig);
  }, []);
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">WORKSPACE BOUNDARIES</div>
        <h1>Know the operating context.</h1>
        <p>Data scope, investigator availability and execution allowances.</p>
      </div>
      <section className="card">
        <h2>Current configuration</h2>
        {config &&
          Object.entries({
            Dataset: "Original synthetic claims/provider-network fixture",
            Investigator: config.model_mode,
            Workflow: config.framework,
            History: config.history_scope,
            "Metric contract": config.contract_version,
            "Maximum returned rows": config.max_rows,
            "Maximum model rounds": config.max_rounds,
            "Maximum SQL attempts": config.max_sql_attempts,
          }).map(([k, v]) => (
            <div className="settings-row" key={k}>
              <span className="muted">{k}</span>
              <strong>{v}</strong>
            </div>
          ))}
      </section>
      <div className="card">
        <h2>Evidence before conclusions</h2>
        <p className="muted">
          The guided baseline exercises known development intents. Live
          investigator quality requires separately recorded model evaluations.
          Query policy checks do not prove clinical or causal conclusions.
        </p>
      </div>
    </>
  );
}

function ProvenanceDrawer({
  result,
  close,
  returnFocus,
}: {
  result: Run["result"];
  close: () => void;
  returnFocus: HTMLButtonElement | null;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      returnFocus?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="drawer"
      aria-label="Execution provenance"
      onCancel={close}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <button className="secondary" autoFocus onClick={close}>
        Close record ×
      </button>
      <h2>Execution provenance</h2>
      <pre>{JSON.stringify(result?.validation, null, 2)}</pre>
      <h3>Token usage</h3>
      <pre>{JSON.stringify(result?.usage, null, 2)}</pre>
    </dialog>
  );
}
