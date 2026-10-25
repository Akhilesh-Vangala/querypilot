import { useState } from "react";
import type { AnalysisResult, Event } from "../../lib/api";
import StudioIcon from "../../components/layout/StudioIcon";
const label = (value: string) => value.replaceAll("_", " ");
const time = (ms: number) => `${(ms / 1000).toFixed(2)}s`;
export default function ExecutionExplorer({
  events,
  result,
  mode,
  status,
  onPlan,
}: {
  events: Event[];
  result?: AnalysisResult | null;
  mode: string;
  status: string;
  onPlan: () => void;
}) {
  const [selected, setSelected] = useState<number | null>(null),
    [filter, setFilter] = useState("all");
  const items = events
    .map((event, index) => ({ event, index }))
    .filter(
      ({ event }) =>
        filter === "all" ||
        (filter === "tools"
          ? !!event.tool ||
            /^(execute_query|execute_comparison|compile_metric_contract)$/.test(
              event.stage,
            )
          : /reconcil|check|validat/.test(event.stage)),
    );
  const active = items.find((e) => e.index === selected) || items.at(-1);
  const live = mode === "live",
    usage = result?.usage;
  const reported =
    usage &&
    Number.isFinite(usage.input_tokens) &&
    Number.isFinite(usage.output_tokens);
  return (
    <section className="agent-explorer" aria-label="Agent execution trace">
      <div className="agent-explorer-heading">
        <span className="agent-orbit" aria-hidden="true">
          <StudioIcon name="query" />
        </span>
        <div>
          <p className="eyebrow">OBSERVED EXECUTION</p>
          <h2>Inside the investigation</h2>
        </div>
        <span className="pill">{label(status)}</span>
      </div>
      <dl className="agent-runtime">
        <div>
          <dt>Investigator</dt>
          <dd>{live ? "Live model" : "Guided baseline"}</dd>
        </div>
        <div>
          <dt>Model tokens</dt>
          <dd>
            {!live
              ? "Not used"
              : reported
                ? `${usage.input_tokens.toLocaleString()} in / ${usage.output_tokens.toLocaleString()} out`
                : "Not reported"}
          </dd>
        </div>
        <div>
          <dt>Authority</dt>
          <dd>Read-only tools</dd>
        </div>
      </dl>
      <div className="agent-trace-toolbar">
        <h3>{events.length} recorded events</h3>
        <label>
          Show{" "}
          <select
            aria-label="Execution event filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All events</option>
            <option value="tools">Tool actions</option>
            <option value="checks">Verification</option>
          </select>
        </label>
      </div>
      <p className="agent-event-caption">
        Timestamps are elapsed since run start. Select an event to inspect its
        public payload.
      </p>
      <ol className="agent-event-list">
        {items.map(({ event: e, index }) => (
          <li key={`${e.sequence}-${index}`}>
            <button
              className="agent-event"
              data-kind={
                e.tool || e.stage.startsWith("execute_")
                  ? "tool"
                  : /reconcil|validat/.test(e.stage)
                    ? "check"
                    : "control"
              }
              aria-pressed={active?.index === index}
              onClick={() => setSelected(index)}
            >
              <span className="agent-event-number">
                {String(e.sequence).padStart(2, "0")}
              </span>
              <span className="agent-event-name">
                <strong>{label(e.stage)}</strong>
                <small>
                  {e.tool ||
                    (e.status === "running" ? "Started" : label(e.status))}
                </small>
              </span>
              <time>{time(e.elapsed_ms)}</time>
            </button>
          </li>
        ))}
      </ol>
      {!items.length && (
        <p className="agent-empty">
          {events.length
            ? "No recorded events match this filter."
            : "Events appear when the server records an execution stage."}
        </p>
      )}
      {active && (
        <div className="agent-event-detail">
          <div>
            <span className="eyebrow">
              SELECTED EVENT / {active.event.sequence}
            </span>
            <h3>{label(active.event.stage)}</h3>
          </div>
          <dl>
            <div>
              <dt>Recorded status</dt>
              <dd>{label(active.event.status)}</dd>
            </div>
            {active.event.tool && (
              <div>
                <dt>Tool</dt>
                <dd>{active.event.tool}</dd>
              </div>
            )}
          </dl>
          <details>
            <summary>Inspect event JSON</summary>
            <pre tabIndex={0} role="region" aria-label="Selected event payload">
              {JSON.stringify(active.event, null, 2)}
            </pre>
          </details>
        </div>
      )}
      {result?.plan && (
        <button className="secondary agent-plan-link" onClick={onPlan}>
          <StudioIcon name="guide" /> Open analysis plan
        </button>
      )}
      <p className="agent-event-caption">
        Public plans and tool events are execution artifacts. They do not expose
        hidden model reasoning.
      </p>
    </section>
  );
}
