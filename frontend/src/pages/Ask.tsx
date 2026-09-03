import { FormEvent, useState } from "react";
import { api, AskResponse } from "../api";
import BarChart from "../components/BarChart";

const EXAMPLES = [
  "What is total revenue last 12 months?",
  "Revenue by family",
  "Which plant produced the most units?",
  "Scrap rate by family",
  "Which DCs had any stockout weeks?",
  "Average freight cost per unit by lane",
];

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4);
  return String(value);
}

export default function Ask() {
  const [question, setQuestion] = useState("Revenue by family");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);

  async function submit(q: string) {
    setBusy(true);
    setError("");
    try {
      setResult(await api.ask(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void submit(question);
  }

  return (
    <>
      <div className="card">
        <h2>Ask the warehouse</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Questions are planned as read-only SQL against the seeded lens star schema. Destructive
          statements are refused before they reach the database.
        </p>
        <div className="chips">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="chip"
              onClick={() => {
                setQuestion(example);
                void submit(example);
              }}
            >
              {example}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit}>
          <label htmlFor="question">Question</label>
          <textarea
            id="question"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
          <div className="form-actions">
            <button type="submit" disabled={busy}>
              {busy ? "Running…" : "Run"}
            </button>
          </div>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </div>

      {result ? (
        <div className="card">
          {result.refused ? <div className="refused">{result.answer}</div> : <p className="answer">{result.answer}</p>}
          {result.sql ? (
            <>
              <h2>SQL</h2>
              <code className="sql-block">{result.sql}</code>
              <p className="muted">Attempts: {result.attempts}</p>
            </>
          ) : null}
          {result.chart === "bar" && result.rows.length > 0 ? (
            <>
              <h2>Chart</h2>
              <BarChart columns={result.columns} rows={result.rows} />
            </>
          ) : null}
          {result.columns.length > 0 ? (
            <>
              <h2>Result</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {result.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j}>{formatCell(cell)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
