import { useEffect, useState } from "react";
import { api, TableInfo } from "../../lib/api";

export default function Schema() {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .schema()
      .then((data) => setTables(data.tables))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load schema"),
      );
  }, []);

  return (
    <>
      <div className="card">
        <div className="eyebrow">AUTHORIZED RELATIONS</div>
        <h1>Explore the warehouse.</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Star schema for healthcare claims and provider-network operations.
          Facts are weekly grain over 80 weeks.
        </p>
        {error ? <p className="error">{error}</p> : null}
      </div>
      {tables.map((table) => (
        <div className="card" key={table.name}>
          <h2>
            {table.name}{" "}
            <span className="muted" style={{ fontWeight: 400 }}>
              {table.row_count_kind === "estimate" ? "≈ " : ""}
              {table.row_count.toLocaleString()} rows
            </span>
          </h2>
          <table>
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col) => (
                <tr key={col.name}>
                  <td className="mono">{col.name}</td>
                  <td className="muted">{col.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}
