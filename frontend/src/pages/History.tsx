import { useEffect, useState } from "react";
import { api, HistoryItem } from "../api";

export default function History() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .history()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"));
  }, []);

  return (
    <div className="card">
      <h2>Recent questions</h2>
      {error ? <p className="error">{error}</p> : null}
      {items.length === 0 && !error ? <p className="muted">No questions yet.</p> : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Question</th>
              <th>Refused</th>
              <th>Answer</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td className="muted">{new Date(item.created_at).toLocaleString()}</td>
                <td>{item.question}</td>
                <td>{item.refused ? "yes" : "no"}</td>
                <td>{item.answer}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
