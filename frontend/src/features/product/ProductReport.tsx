import { useState } from "react";
import { useProduct } from "./context";
import { download } from "./lib/api";
import { Definition, Dialog, Heading, Issue, Steps, Table } from "./components";
function compare(a: string, b: string, absolute = false): number {
  const negA = a.startsWith("-"),
    negB = b.startsWith("-");
  if (!absolute && negA !== negB) return negA ? -1 : 1;
  const [intA, fracA = ""] = a.replace(/^[-+]/, "").split("."),
    [intB, fracB = ""] = b.replace(/^[-+]/, "").split(".");
  const x = intA.replace(/^0+/, "") || "0",
    y = intB.replace(/^0+/, "") || "0",
    n = Math.max(fracA.length, fracB.length);
  const result =
    x.length !== y.length
      ? Math.sign(x.length - y.length)
      : x !== y
        ? x > y
          ? 1
          : -1
        : fracA.padEnd(n, "0") === fracB.padEnd(n, "0")
          ? 0
          : fracA.padEnd(n, "0") > fracB.padEnd(n, "0")
            ? 1
            : -1;
  return !absolute && negA ? -result : result;
}
export default function ProductReport({
  save,
  clear,
}: {
  save: () => void;
  clear: () => void;
}) {
  const ctx = useProduct(),
    { draft } = ctx,
    report = draft.report!;
  const [tab, setTab] = useState("overview"),
    [offset, setOffset] = useState(0),
    [descending, setDescending] = useState(true),
    [inspect, setInspect] = useState(false);
  const ids = ["overview", "quality", "calculation"],
    s = report.summary;
  const ordered = [...report.results].sort(
    (a, b) => (descending ? -1 : 1) * compare(a.value, b.value),
  );
  const largest = [...report.results]
      .sort((a, b) => -compare(a.value, b.value, true))
      .slice(0, 8),
    maximum = Math.max(...largest.map((r) => Math.abs(Number(r.value))), 1),
    negative = largest.some((r) => r.value.startsWith("-"));
  return (
    <div id="output">
      <Heading
        eyebrow="ANALYTICAL REPORT"
        title={draft.title}
        description={draft.filename + " · " + s.source_rows + " source records"}
        actions={
          <>
            <button
              className="secondary"
              onClick={() =>
                ctx.setDraft((d) => ({
                  ...d,
                  stage: d.csv ? 1 : 0,
                  report: null,
                  dirty: true,
                }))
              }
            >
              Edit rules & rerun
            </button>
            <button className="primary" onClick={save}>
              Save analysis
            </button>
            <button id="clear" className="quiet" onClick={clear}>
              Clear workspace
            </button>
          </>
        }
      />
      <Steps active={3} />
      <Issue />
      <section className="finding-hero">
        <p className="eyebrow">EXECUTED EVIDENCE</p>
        <h2>
          {s.operation === "average"
            ? "An average with the right denominator."
            : s.operation === "count"
              ? "A count grounded in the selected records."
              : "A total reconciled from the source."}
        </h2>
        <p>
          {s.included_rows} included records across {s.groups} groups. SQL sums
          and counts agree with the independent Decimal computation. This is a
          descriptive result under your selected rules, not a causal conclusion.
        </p>
        <div className="spaced" id="verification">
          <span className="badge">Independent checks passed</span>
        </div>
      </section>
      {report.run_record && (
        <section className="report-lineage" aria-label="Execution provenance">
          <div>
            <span className="eyebrow">EXECUTION MODE</span>
            <strong>
              {report.run_record.mode === "reviewed-aggregate"
                ? "Reviewed aggregate"
                : report.run_record.mode}
            </strong>
          </div>
          <div>
            <span className="eyebrow">VERIFICATION</span>
            <strong>
              {report.run_record.check_count} independent{" "}
              {report.run_record.check_count === 1 ? "check" : "checks"}
            </strong>
          </div>
          <div>
            <span className="eyebrow">MODEL USAGE</span>
            <strong>
              {report.run_record.billing === "not-used"
                ? "No model calls"
                : report.run_record.billing}
            </strong>
          </div>
          <details>
            <summary>Inspect run identity</summary>
            <dl>
              <dt>Run ID</dt>
              <dd>{report.run_record.run_id}</dd>
              <dt>Verification scope</dt>
              <dd>{report.run_record.verification_scope}</dd>
              <dt>Contract SHA-256</dt>
              <dd>{report.run_record.contract_sha256}</dd>
              <dt>Result SHA-256</dt>
              <dd>{report.run_record.result_sha256}</dd>
            </dl>
          </details>
        </section>
      )}
      <div className="stats spaced">
        {[
          [
            s.operation === "average"
              ? "Overall weighted average"
              : s.operation === "count"
                ? "Included record count"
                : "Overall sum",
            s.overall_value,
            s.operation === "average"
              ? "All included values ÷ actual included rows"
              : "Exact decimal result",
          ],
          ["Included records", s.included_rows, "From the reviewed filter"],
          [
            "Excluded records",
            s.excluded_rows,
            "No implicit cleaning or deduplication",
          ],
        ].map(([label, value, hint]) => (
          <div className="stat" key={String(label)}>
            <span className="stat-label">{label}</span>
            <strong className="exact-value">{value}</strong>
            <small>{hint}</small>
          </div>
        ))}
      </div>
      <div className="tabs" role="tablist" aria-label="Report sections">
        {[
          ["overview", "Overview"],
          ["quality", "Source quality"],
          ["calculation", "SQL & checks"],
        ].map(([id, label]) => (
          <button
            key={id}
            role="tab"
            id={"tab-" + id}
            aria-controls="report-panel"
            aria-selected={tab === id}
            tabIndex={tab === id ? 0 : -1}
            onClick={() => setTab(id)}
            onKeyDown={(e) => {
              if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
                e.preventDefault();
                const index = ids.indexOf(id),
                  next =
                    e.key === "Home"
                      ? ids[0]
                      : e.key === "End"
                        ? ids[2]
                        : ids[(index + (e.key === "ArrowRight" ? 1 : 2)) % 3];
                setTab(next);
                requestAnimationFrame(() =>
                  document.getElementById("tab-" + next)?.focus(),
                );
              }
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <div id="report-panel" role="tabpanel" aria-labelledby={"tab-" + tab}>
        {tab === "overview" && (
          <div className="result-grid">
            <section className="panel">
              <h2>Where the result comes from</h2>
              <p className="hint spaced">
                Largest groups by absolute value. Bar widths are approximate;
                labels and the table retain exact decimal strings.
              </p>
              <div
                className="segment-chart"
                role="list"
                aria-label="Largest analytical groups"
              >
                {largest.map((r) => (
                  <div className="segment-row" key={r.segment} role="listitem">
                    <span className="segment-label" title={r.segment}>
                      {r.segment || "(empty)"}
                    </span>
                    <svg
                      viewBox="0 0 100 12"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      <rect
                        x={
                          negative
                            ? r.value.startsWith("-")
                              ? 50 - (Math.abs(Number(r.value)) / maximum) * 48
                              : 50
                            : 0
                        }
                        y={2}
                        height={8}
                        rx={1}
                        width={
                          (Math.abs(Number(r.value)) / maximum) *
                          (negative ? 48 : 100)
                        }
                        fill={r.value.startsWith("-") ? "#c4523f" : "#6850d8"}
                      />
                      {negative && (
                        <line
                          x1={50}
                          x2={50}
                          y1={0}
                          y2={12}
                          stroke="#aaa"
                          strokeWidth={0.5}
                        />
                      )}
                    </svg>
                    <span className="segment-value">{r.value}</span>
                  </div>
                ))}
              </div>
              <div className="preview-controls">
                <span>All verified groups</span>
                <button
                  className="quiet"
                  onClick={() => {
                    setDescending(!descending);
                    setOffset(0);
                  }}
                >
                  Sort value {descending ? "↓" : "↑"}
                </button>
              </div>
              <Table
                label="Exact analytical results"
                headers={["Segment", s.operation, "Records"]}
                rows={ordered
                  .slice(offset, offset + 10)
                  .map((r) => [r.segment || "(empty)", r.value, r.records])}
              />
              <div className="pager">
                <span>
                  {offset + 1}–{Math.min(offset + 10, ordered.length)} of{" "}
                  {ordered.length}
                </span>
                <div className="actions">
                  <button
                    className="quiet"
                    disabled={!offset}
                    onClick={() => setOffset(offset - 10)}
                  >
                    ← Previous
                  </button>
                  <button
                    className="quiet"
                    disabled={offset + 10 >= ordered.length}
                    onClick={() => setOffset(offset + 10)}
                  >
                    Next →
                  </button>
                </div>
              </div>
            </section>
            <aside className="stack">
              <section className="panel">
                <h2>Keep the business definition visible.</h2>
                <Definition />
                <p className="hint spaced">
                  No unit or currency is inferred from a number. Interpret
                  results using the source measure’s units.
                </p>
                <button
                  className="secondary spaced"
                  onClick={() =>
                    ctx.setDraft((d) => ({
                      ...d,
                      stage: d.csv ? 1 : 0,
                      report: null,
                      dirty: true,
                    }))
                  }
                >
                  Edit rules & rerun
                </button>
              </section>
              <section className="panel">
                <h3>The boundary of this result</h3>
                <p className="muted spaced">{report.scope}</p>
              </section>
            </aside>
          </div>
        )}
        {tab === "quality" && (
          <section className="panel">
            <h2>Source quality remains inspectable.</h2>
            <p className="hint spaced">
              Missing or malformed included numeric measures withhold a report.
              Count does not require a numeric measure. Repeated rows are
              retained under the reviewed contract.
            </p>
            <Table
              label="Source column quality"
              headers={["Column", "Missing", "Numeric", "Distinct"]}
              rows={(draft.profile?.columns || []).map((c) => [
                c.name,
                c.missing ?? "See retained source",
                c.numeric ?? "—",
                c.distinct ?? "—",
              ])}
            />
            <button
              className="secondary spaced"
              onClick={() =>
                ctx.setDraft((d) => ({ ...d, stage: 0, report: null }))
              }
            >
              Inspect original source
            </button>
          </section>
        )}
        {tab === "calculation" && (
          <section className="panel">
            <h2>The executed query and independent checks.</h2>
            <pre className="spaced">{report.sql}</pre>
            <p className="hint spaced">
              The SQL targets a request-local normalized records table. It needs
              adaptation before warehouse use; no uploaded SQL is executed.
            </p>
            <Table
              label="SQL normalization bindings"
              headers={["Normalized field", "Source binding"]}
              rows={Object.entries(report.column_bindings)}
            />
            {Object.entries(report.checks).map(([name, value]) => (
              <div className="check-row spaced" key={name}>
                <span aria-hidden="true">✓</span>
                <div>
                  <strong>{name.replaceAll("_", " ")}</strong>
                  <p>{value ? "Passed" : "Failed"}</p>
                </div>
              </div>
            ))}
            <button
              className="secondary spaced"
              onClick={() =>
                download(
                  "-- Normalized request-local aggregate; adapt source bindings before warehouse use.\n" +
                    report.sql +
                    ";\n",
                  "querypilot-normalized-query.sql",
                  "text/plain",
                )
              }
            >
              Download normalized SQL
            </button>
          </section>
        )}
      </div>
      <section className="panel spaced">
        <div className="panel-heading">
          <h2>Keep the evidence with the answer.</h2>
          <span className="badge">
            {draft.storage === "memory" ? "Not saved" : "Saved snapshot"}
          </span>
        </div>
        <div className="actions spaced">
          <button
            className="secondary"
            id="download-json"
            onClick={() =>
              download(
                JSON.stringify(report, null, 2),
                "querypilot-evidence.json",
              )
            }
          >
            Download evidence JSON
          </button>
          <button
            className="primary"
            id="download-csv"
            onClick={() =>
              download(report.csv, "querypilot-results.csv", "text/csv")
            }
          >
            Download results CSV
          </button>
          <button
            className="quiet"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(
                  draft.title +
                    "\n" +
                    s.operation +
                    ": " +
                    s.overall_value +
                    "\nSource SHA-256: " +
                    report.source_sha256,
                );
                ctx.notify("Report summary copied.");
              } catch {
                ctx.notify(
                  "Clipboard access was unavailable. Use the evidence download instead.",
                );
              }
            }}
          >
            Copy report summary
          </button>
          <button className="quiet" onClick={() => setInspect(true)}>
            Inspect source & rules
          </button>
        </div>
        <p className="hint spaced">
          Verified {new Date(report.verified_at).toLocaleString()} · A past
          source-snapshot calculation.
        </p>
        <p className="report-source mono">
          Source SHA-256 · {report.source_sha256}
        </p>
        <details id="evidence" className="spaced">
          <summary>Complete evidence JSON</summary>
          <pre>{JSON.stringify(report, null, 2)}</pre>
        </details>
      </section>
      {inspect && (
        <Dialog
          title="Source and reviewed definition"
          onClose={() => setInspect(false)}
        >
          <p>{draft.filename}</p>
          <Definition />
          <p className="hint spaced">
            Saved results authenticate a past calculation; they do not recheck a
            live source system.
          </p>
          <div className="dialog-actions">
            <button className="secondary" onClick={() => setInspect(false)}>
              Close
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
