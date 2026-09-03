import { useState } from "react";
import { api, EvalReport } from "../api";

export default function EvalPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    try {
      setReport(await api.evalRun());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval failed (admin role required)");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Golden eval</h2>
      <p className="muted">
        Runs the 12-question harness and scores <em>execution accuracy</em>: predicted SQL and gold SQL
        must return the same result set, not the same tokens. With no API key the predicted SQL comes
        from the intent compiler, which is written separately from the gold file.
      </p>
      <div className="form-actions">
        <button type="button" onClick={() => void run()} disabled={busy}>
          {busy ? "Scoring…" : "Run eval"}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {report ? (
        <>
          <p className="score">{(report.score * 100).toFixed(1)}%</p>
          <p className="muted">
            {report.passed} / {report.n} questions matched
          </p>
          <table>
            <thead>
              <tr>
                <th>Case</th>
                <th>Result</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {report.results.map((row) => (
                <tr key={row.id}>
                  <td>{row.question}</td>
                  <td>{row.passed ? "pass" : "fail"}</td>
                  <td className="muted">{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </div>
  );
}
