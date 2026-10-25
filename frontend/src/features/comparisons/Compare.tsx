import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, Metric } from "../../lib/api";

const labels: Record<string, string> = {
  claims_paid: "claims paid",
  declined_referral_rate: "declined referral rate",
  referral_wait: "referral wait",
  closed_panels: "closed panels",
  coordination_cost: "coordination cost",
};

export default function Compare() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [metric, setMetric] = useState("claims_paid"),
    [dimension, setDimension] = useState("specialty");
  const [beforeStart, setBeforeStart] = useState("2026-01-01"),
    [beforeEnd, setBeforeEnd] = useState("2026-04-01");
  const [afterStart, setAfterStart] = useState("2026-04-01"),
    [afterEnd, setAfterEnd] = useState("2026-07-01");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    api
      .metrics()
      .then((r) => setMetrics(r.metrics))
      .catch(() => setError("Unable to load reviewed metrics."));
  }, []);
  useEffect(() => {
    const selection = metrics.find((m) => m.id === params.get("metric"));
    if (selection) {
      setMetric(selection.id);
      setDimension(
        selection.comparison_dimensions.includes(params.get("dimension") || "")
          ? params.get("dimension")!
          : selection.comparison_dimensions[0],
      );
    }
  }, [metrics, params]);
  const selected = metrics.find((m) => m.id === metric);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      beforeStart >= beforeEnd ||
      afterStart >= afterEnd ||
      beforeEnd > afterStart
    ) {
      setError(
        "Choose nonoverlapping periods, baseline first. End dates are exclusive.",
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      const question = `Compare ${labels[metric]} from ${beforeStart} to ${beforeEnd} versus ${afterStart} to ${afterEnd} by ${dimension}`;
      const run = await api.createAnalysis(question, "baseline");
      navigate("/runs/" + run.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparison failed");
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <Link className="back-link" to="/">
          ← Overview
        </Link>
        <div className="eyebrow">EXECUTABLE ANALYTICAL CONTRACT</div>
        <h1>Understand what changed.</h1>
        <p>
          Compare two periods, reconcile the breakdown, and inspect the evidence
          behind each contribution.
        </p>
      </div>
      <div className="two-columns">
        <section className="card">
          <h2>Define the comparison</h2>
          <form onSubmit={submit}>
            <div className="form-grid">
              <div>
                <label htmlFor="metric">Reviewed metric</label>
                <select
                  id="metric"
                  value={metric}
                  onChange={(e) => {
                    setMetric(e.target.value);
                    setDimension(
                      metrics.find((m) => m.id === e.target.value)!
                        .comparison_dimensions[0],
                    );
                  }}
                >
                  {metrics.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="dimension">Break down by</label>
                <select
                  id="dimension"
                  value={dimension}
                  onChange={(e) => setDimension(e.target.value)}
                >
                  {selected?.comparison_dimensions.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <fieldset>
              <legend>Baseline period</legend>
              <div className="form-grid">
                <div>
                  <label htmlFor="before-start">Baseline start</label>
                  <input
                    id="before-start"
                    type="date"
                    required
                    value={beforeStart}
                    onChange={(e) => setBeforeStart(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="before-end">Baseline end · exclusive</label>
                  <input
                    id="before-end"
                    type="date"
                    required
                    value={beforeEnd}
                    onChange={(e) => setBeforeEnd(e.target.value)}
                  />
                </div>
              </div>
            </fieldset>
            <fieldset>
              <legend>Comparison period</legend>
              <div className="form-grid">
                <div>
                  <label htmlFor="after-start">Comparison start</label>
                  <input
                    id="after-start"
                    type="date"
                    required
                    value={afterStart}
                    onChange={(e) => setAfterStart(e.target.value)}
                  />
                </div>
                <div>
                  <label htmlFor="after-end">Comparison end · exclusive</label>
                  <input
                    id="after-end"
                    type="date"
                    required
                    value={afterEnd}
                    onChange={(e) => setAfterEnd(e.target.value)}
                  />
                </div>
              </div>
            </fieldset>
            <p className="muted">
              Weekly source snapshots. Each period can span up to 366 days.
              Missing coverage or invalid denominators withhold the conclusion.
            </p>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="form-actions">
              <button disabled={busy || !selected}>
                {busy ? "Investigating change…" : "Investigate change ↗"}
              </button>
            </div>
          </form>
        </section>
        <aside>
          <div className="card feature-card">
            <div className="eyebrow">THE INVESTIGATION</div>
            <h2>More than two totals.</h2>
            <ol className="flow-list">
              <li>
                <span>01</span>
                <div>
                  <strong>Compile the definition</strong>
                  <p>
                    Approved joins, numerator, denominator and explicit windows.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <strong>Execute one snapshot</strong>
                  <p>
                    Both periods, independent totals and segment aggregates in
                    one read-only statement.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <strong>Reconcile the evidence</strong>
                  <p>
                    Check coverage, input quality, denominators and contribution
                    totals.
                  </p>
                </div>
              </li>
              <li>
                <span>04</span>
                <div>
                  <strong>Explain the change</strong>
                  <p>
                    Claims spend separates volume, segment mix and unit cost
                    using Shapley accounting.
                  </p>
                </div>
              </li>
            </ol>
          </div>
          <div className="card">
            <h3>Explicit analytical scope</h3>
            <p className="muted">
              This form uses the guided compiler without a model call. A
              configured live investigator can select the same typed tool from a
              flexible question. Accounting contributions describe change; they
              do not establish causes.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
