import { useEffect, useId, useRef, type ReactNode } from "react";
import { useProduct } from "./context";
export function Heading({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1 tabIndex={-1}>{title}</h1>
        <p className="muted spaced">{description}</p>
      </div>
      <div className="actions">{actions}</div>
    </header>
  );
}
export function Table({
  headers,
  rows,
  label,
}: {
  headers: string[];
  rows: ReactNode[][];
  label: string;
}) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label={label}>
      <table>
        <caption className="sr-only">{label}</caption>
        <thead>
          <tr>
            {headers.map((h) => (
              <th scope="col" key={h}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, n) => (
                <td key={n}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Dialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    return () => {
      ref.current?.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <dialog ref={ref} open={undefined} onClose={onClose} aria-labelledby={id}>
      <div className="dialog-heading">
        <h2 id={id}>{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Issue({ inspect }: { inspect?: (rows: number[]) => void }) {
  const { problem, setProblem } = useProduct();
  if (!problem) return null;
  return (
    <section className="issue-box" id="error" role="alert" tabIndex={-1}>
      <p className="eyebrow">REVIEW NEEDED</p>
      <h2>Let’s resolve this before publishing a result.</h2>
      <p className="spaced">{problem.message}</p>
      {problem.hint && <p className="muted spaced">{problem.hint}</p>}
      <ul className="issue-list">
        {problem.issues.map((i, n) => (
          <li key={n}>
            {i.row
              ? "Record " + i.row + (i.column ? " · " + i.column : "") + ": "
              : ""}
            {i.message}
          </li>
        ))}
      </ul>
      <div className="actions spaced">
        {inspect && problem.issues.some((i) => (i.row || 0) > 1) && (
          <button
            className="secondary"
            onClick={() =>
              inspect([
                ...new Set(
                  problem.issues.flatMap((i) =>
                    i.row && i.row > 1 ? [i.row] : [],
                  ),
                ),
              ])
            }
          >
            Inspect affected records
          </button>
        )}
        <button className="quiet" onClick={() => setProblem(null)}>
          Dismiss
        </button>
      </div>
    </section>
  );
}
export function Steps({ active }: { active: number }) {
  return (
    <ol className="wizard-steps" aria-label="Analysis steps">
      {["Source", "Metric rules", "Review", "Results"].map((name, n) => (
        <li
          key={name}
          className={n === active ? "active" : n < active ? "complete" : ""}
          aria-current={n === active ? "step" : undefined}
        >
          <span className="step-number">
            {n < active ? "✓" : "0" + (n + 1)}
          </span>
          {name}
        </li>
      ))}
    </ol>
  );
}
export function Definition() {
  const { draft } = useProduct(),
    name = (key: string) =>
      draft.profile?.columns.find((c) => c.id === draft.mapping[key])?.name ||
      "Not mapped";
  return (
    <div className="definition">
      <p>
        <strong>{draft.options.operation || "sum"}</strong>
        {draft.options.operation === "count"
          ? " of source records"
          : " of " + name("measure")}
        .{" "}
        {draft.mapping.group
          ? "Group by " + name("group") + "."
          : "Return one overall result."}
      </p>
      <p className="spaced">
        {draft.mapping.filter
          ? "Include only " +
            name("filter") +
            " exactly equal to “" +
            (draft.options.filter_value || "") +
            "”."
          : "Include every source record."}
      </p>
      <p className="hint spaced">
        Duplicates are retained. Included missing or malformed measures stop the
        calculation. No currency, imputation or causal explanation is inferred.
      </p>
    </div>
  );
}
