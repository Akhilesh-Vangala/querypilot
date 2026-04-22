type Props = {
  columns: string[];
  rows: unknown[][];
};

function isNumeric(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export default function BarChart({ columns, rows }: Props) {
  if (rows.length === 0 || columns.length < 2) return null;

  const labelIndex = columns.findIndex((_, i) =>
    rows.some((row) => typeof row[i] === "string"),
  );
  const valueIndex = columns.findIndex((_, i) =>
    rows.some((row) => isNumeric(row[i])),
  );
  if (labelIndex < 0 || valueIndex < 0) return null;

  const values = rows.map((row) => Math.abs(Number(row[valueIndex]) || 0));
  const max = Math.max(...values, 1);

  return (
    <div>
      {rows.map((row, idx) => {
        const label = String(row[labelIndex] ?? "");
        const value = Number(row[valueIndex]) || 0;
        const width = (Math.abs(value) / max) * 100;
        return (
          <div className="bar-row" key={`${label}-${idx}`}>
            <span>{label}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${width}%` }} />
            </div>
            <span className="mono">
              {Number.isInteger(value) ? value : value.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
