import { ACCEPT, FORMAT_HELP } from "./lib/imports";
import { useEffect, useState, type ChangeEvent } from "react";
import { useProduct } from "./context";
import { request } from "./lib/api";
import type { SourceRow } from "./types";
import { Definition, Heading, Issue, Steps, Table } from "./components";
export const STAGES = [
  ["source", "Inspect source records"],
  ["contract", "Validate metric and filter"],
  ["sql", "Execute the generated aggregate"],
  ["reference", "Compute the independent Decimal reference"],
  ["reconcile", "Reconcile exact sums and actual counts"],
  ["report", "Prepare the checked analytical report"],
];
export default function ProductIntake({
  save,
  clear,
}: {
  save: () => void;
  clear: () => void;
}) {
  const ctx = useProduct(),
    { draft, busy, stages } = ctx;
  const [confirm, setConfirm] = useState(false),
    [offset, setOffset] = useState(0),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState<number[]>([]),
    [preview, setPreview] = useState<{
      rows: SourceRow[];
      matches: number;
    } | null>(null),
    [previewError, setPreviewError] = useState("");
  useEffect(() => {
    setConfirm(false);
  }, [draft.stage]);
  useEffect(() => {
    setPreview(null);
    setOffset(0);
    setSearch("");
    setSelected([]);
  }, [draft.csv]);
  useEffect(() => {
    if (!draft.csv) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPreviewError("");
      request<{ rows: SourceRow[]; matches: number }>(
        "/api/uploads/preview",
        { csv: draft.csv, offset, search, rows: selected },
        controller.signal,
      )
        .then(setPreview)
        .catch((e) => {
          if (e.name !== "AbortError") setPreviewError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search, offset, selected, draft.csv]);
  function next(stage: number) {
    if (stage > 0 && (!draft.csv || !draft.profile)) {
      ctx.fail(Error("Choose a valid source file first."));
      return;
    }
    if (
      stage === 2 &&
      draft.options.operation !== "count" &&
      !draft.mapping.measure
    ) {
      ctx.fail(Error("Choose a numeric measure before continuing."));
      return;
    }
    ctx.setProblem(null);
    setConfirm(false);
    ctx.setDraft((d) => ({ ...d, stage }));
    window.scrollTo({ top: 0 });
  }
  function file(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files?.[0]) ctx.loadFile(event.target.files[0]);
    event.target.value = "";
  }
  const records = preview?.rows || draft.profile?.preview || [],
    matches = preview?.matches ?? draft.profile?.rows ?? 0;
  return (
    <>
      <Heading
        eyebrow="NEW ANALYSIS"
        title={
          draft.title === "Untitled analysis"
            ? "Start with the source."
            : draft.title
        }
        description="A precise path from your export to an independently checked analytical result."
        actions={
          <>
            <a className="quiet" href="/uploads/recording.html">
              Watch upload demo
            </a>
            <button
              className="secondary"
              disabled={!draft.csv || busy}
              onClick={save}
            >
              Save draft
            </button>
            <button
              className="quiet"
              id="clear"
              disabled={busy}
              onClick={clear}
            >
              Clear workspace
            </button>
          </>
        }
      />
      <Steps active={draft.stage} />
      <Issue
        inspect={(rows) => {
          ctx.setDraft((d) => ({ ...d, stage: 0 }));
          setSearch("");
          setOffset(0);
          setSelected(rows);
        }}
      />
      {draft.stage === 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Bring the data behind the question.</h2>
              <p className="hint spaced">
                We’ll inspect the source before you define the metric.
              </p>
            </div>
            {draft.sourceKind === "sample" && (
              <span className="badge">Sample data</span>
            )}
          </div>
          <div className="upload-grid">
            <div>
              <label
                className="dropzone"
                id="dropzone"
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = "copy";
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files.length !== 1) {
                    ctx.fail(Error("Choose one tabular file at a time."));
                    return;
                  }
                  ctx.loadFile(e.dataTransfer.files[0]);
                }}
              >
                <span className="eyebrow">TABULAR SOURCE</span>
                <strong>Choose a file or drop it here</strong>
                <span>{FORMAT_HELP} · 5,000 records</span>
                <input
                  id="file"
                  type="file"
                  accept={ACCEPT}
                  onChange={file}
                  disabled={busy}
                />
              </label>
              {draft.filename && (
                <div className="file-summary spaced" id="file-info">
                  <div>
                    <strong>{draft.filename}</strong>
                    <p>
                      {draft.profile && draft.csv
                        ? draft.profile.rows +
                          " records · " +
                          draft.profile.columns.length +
                          " columns"
                        : "Re-upload the original source to continue"}
                    </p>
                  </div>
                </div>
              )}
            </div>
            <aside className="help-card">
              <h3>Prepare a source you can interpret.</h3>
              <p>
                Include one header row and consistent units. Duplicates remain
                in the analysis; included invalid numeric values are refused.
              </p>
              <a href="/api/uploads/template" className="secondary" download>
                Download CSV template
              </a>
            </aside>
          </div>
          <div className="form-grid spaced">
            <label className="field">
              Analysis name
              <input
                id="analysis-title"
                maxLength={100}
                value={draft.title}
                onChange={(e) =>
                  ctx.setDraft((d) => ({
                    ...d,
                    title: e.target.value,
                    dirty: true,
                  }))
                }
              />
            </label>
            <label className="field">
              Project
              <select
                id="project-select"
                value={draft.projectId}
                onChange={(e) =>
                  ctx.setDraft((d) => ({
                    ...d,
                    projectId: e.target.value,
                    dirty: true,
                  }))
                }
              >
                <option value="">Unassigned</option>
                {ctx.projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name +
                      " · " +
                      (p.storage === "cloud" ? "Account" : "This device")}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {draft.importSource && (
            <div className="callout">
              <p>
                Imported{" "}
                {String(draft.importSource.format || "table")
                  .slice(0, 12)
                  .toUpperCase()}
                {draft.importSource.sheet
                  ? " · Worksheet: " + draft.importSource.sheet
                  : ""}
                . Review source values and mappings. Original formatting and
                formulas are not used.
              </p>
            </div>
          )}
          {draft.profile && draft.csv && (
            <div className="spaced">
              <h3>Inspect the actual records.</h3>
              <div className="preview-controls">
                <span id="preview-count">{matches} matching records</span>
                <label className="search-field">
                  Find a value
                  <input
                    type="search"
                    aria-label="Search source records"
                    maxLength={120}
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setOffset(0);
                      setSelected([]);
                    }}
                  />
                </label>
              </div>
              {previewError && (
                <p role="alert" className="inline-error">
                  {previewError}
                </p>
              )}
              <div id="preview-content" className="data-preview">
                <Table
                  label="Source record preview"
                  headers={[
                    "Record",
                    ...draft.profile.columns.map((c) => c.name),
                  ]}
                  rows={records.map((r) => [r.row, ...r.cells])}
                />
              </div>
              <div className="pager">
                <span>Logical record numbers include the header as 1.</span>
                <div className="actions">
                  <button
                    className="quiet"
                    id="preview-prev"
                    disabled={!offset}
                    onClick={() => setOffset(Math.max(0, offset - 25))}
                  >
                    ← Previous
                  </button>
                  <button
                    className="quiet"
                    id="preview-next"
                    disabled={offset + 25 >= matches}
                    onClick={() => setOffset(offset + 25)}
                  >
                    Next →
                  </button>
                </div>
              </div>
              <details className="spaced">
                <summary>Column quality and numeric coverage</summary>
                <Table
                  label="Source column profile"
                  headers={["Column", "Missing", "Numeric", "Distinct"]}
                  rows={draft.profile.columns.map((c) => [
                    c.name,
                    c.missing,
                    c.numeric + " / " + draft.profile!.rows,
                    c.distinct,
                  ])}
                />
              </details>
            </div>
          )}
          <div className="wizard-footer">
            <p className="hint">
              Source content is not added to history unless you explicitly save.
            </p>
            <button
              className="primary"
              id="review-rules"
              disabled={!draft.csv || !draft.profile || busy}
              onClick={() => next(1)}
            >
              Review metric rules →
            </button>
          </div>
        </section>
      )}
      {draft.stage === 1 && (
        <section className="panel" id="contract">
          <h2>Define the analytical question precisely.</h2>
          <p className="hint spaced">
            Suggested bindings need your review. The name is a label; it is not
            interpreted by a live model.
          </p>
          <form
            id="form"
            onSubmit={(e) => {
              e.preventDefault();
              next(2);
            }}
          >
            <div className="form-grid spaced">
              <label className="field">
                Operation
                <select
                  id="operation"
                  value={draft.options.operation || "sum"}
                  onChange={(e) =>
                    ctx.update({
                      options: { ...draft.options, operation: e.target.value },
                    })
                  }
                >
                  {["sum", "count", "average"].map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
                <span className="hint">
                  Average uses the actual record count, never the average of
                  group averages.
                </span>
              </label>
              {(
                [
                  [
                    "measure",
                    "Numeric measure",
                    draft.options.operation !== "count",
                  ],
                  ["group", "Break down by", false],
                  ["filter", "Exact-match filter column", false],
                ] as const
              ).map(([key, label, required]) => (
                <label key={key} className="field">
                  {label + (required ? " *" : "")}
                  <select
                    id={"mapping-" + key}
                    required={required}
                    value={draft.mapping[key] || ""}
                    onChange={(e) => {
                      const mapping = { ...draft.mapping };
                      if (e.target.value) mapping[key] = e.target.value;
                      else delete mapping[key];
                      const options = { ...draft.options };
                      if (key === "filter" && !e.target.value)
                        delete options.filter_value;
                      ctx.update({ mapping, options });
                    }}
                  >
                    <option value="">
                      {required ? "Choose a column…" : "None"}
                    </option>
                    {draft.profile?.columns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {draft.mapping.filter && (
                <label className="field">
                  Include this exact value
                  <input
                    id="filter-value"
                    maxLength={120}
                    value={draft.options.filter_value || ""}
                    onChange={(e) =>
                      ctx.update({
                        options: {
                          ...draft.options,
                          filter_value: e.target.value,
                        },
                      })
                    }
                  />
                  <span className="hint">
                    Case-sensitive. An empty value matches empty source cells.
                  </span>
                </label>
              )}
            </div>
            <div className="callout spaced">
              <p>
                All source rows, including repeated rows, remain eligible unless
                excluded by your selected filter. No missing value is imputed.
              </p>
            </div>
            <div className="wizard-footer">
              <button
                type="button"
                className="secondary"
                onClick={() => next(0)}
              >
                ← Back to source
              </button>
              <button className="primary" id="review-definition" type="submit">
                Review definition →
              </button>
            </div>
          </form>
        </section>
      )}
      {draft.stage === 2 && (
        <section className="panel">
          <p className="eyebrow">CONFIRM THE ANALYTICAL SCOPE</p>
          <h2 className="spaced">Here is the calculation we’ll verify.</h2>
          <Definition />
          <p className="muted spaced">
            The generated read-only SQL is reconciled against an independent
            Decimal aggregation. Empty filter results and malformed included
            values withhold the report.
          </p>
          <label className="checkbox spaced">
            <input
              type="checkbox"
              id="confirm-rules"
              checked={confirm}
              onChange={(e) => setConfirm(e.target.checked)}
            />
            I reviewed the operation, measure, grouping, filter and source
            assumptions.
          </label>
          <div className="wizard-footer">
            <button className="secondary" onClick={() => next(1)}>
              ← Edit rules
            </button>
            <button
              className="primary"
              id="analyze"
              disabled={!confirm || busy}
              onClick={ctx.run}
            >
              Run verification →
            </button>
          </div>
        </section>
      )}
      {draft.stage === 3 && busy && (
        <section className="panel" aria-busy="true">
          <h2>Executing the reviewed question.</h2>
          <p className="hint spaced" role="status">
            Progress reflects observed server stages; no synthetic percentages.
          </p>
          <div className="progress-list">
            {STAGES.map(([id, name]) => (
              <div
                className="progress-stage"
                data-stage={id}
                data-state={stages[id] || "pending"}
                key={id}
              >
                <span className="stage-icon" aria-hidden="true">
                  {stages[id] === "complete"
                    ? "✓"
                    : stages[id] === "running"
                      ? "…"
                      : "·"}
                </span>
                <div>
                  <h3>{name}</h3>
                  <p>{stages[id] || "Pending"}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="wizard-footer">
            <span className="hint">Your source file is never modified.</span>
            <button className="secondary" onClick={ctx.stop}>
              Stop waiting
            </button>
          </div>
        </section>
      )}
    </>
  );
}
