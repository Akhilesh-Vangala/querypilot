import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Run } from "../api";
export default function History() {
  const [items, setItems] = useState<Run[]>([]),
    [error, setError] = useState(""),
    [filter, setFilter] = useState("");
  useEffect(() => {
    api
      .analyses()
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);
  const rows = items.filter((r) =>
    r.question.toLowerCase().includes(filter.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">YOUR ANALYTICAL RECORDS</div>
        <div className="section-heading">
          <div>
            <h1>Investigations.</h1>
            <p>
              Open an executed query, its plan, and the evidence behind the
              answer.
            </p>
          </div>
          <Link className="button" to="/new">
            New investigation ↗
          </Link>
        </div>
      </div>
      <div className="card">
        <label htmlFor="search">Find a question</label>
        <input
          id="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search investigations…"
        />
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {rows.map((r) => (
          <Link className="run-row" to={"/runs/" + r.id} key={r.id}>
            <div>
              <strong>{r.question}</strong>
              <small>
                {r.mode} · {new Date(r.created_at).toLocaleString()}
              </small>
            </div>
            <span className="pill">{r.status.replaceAll("_", " ")}</span>
          </Link>
        ))}
        {rows.length === 0 && !error && (
          <div className="empty-state">
            <h3>No matching investigations.</h3>
            <Link to="/new">Ask your next question →</Link>
          </div>
        )}
      </div>
    </>
  );
}
