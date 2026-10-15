import { ComparisonReport as Report, Run } from "../../lib/api";

const number = (value: number | null | undefined, signed = false) =>
  value == null
    ? "Undefined"
    : (Math.abs(value) < 1e-8 ? 0 : value).toLocaleString(undefined, {
        maximumFractionDigits: 4,
        signDisplay: signed ? "exceptZero" : "auto",
      });

export function exportReport(run: Run) {
  const blob = new Blob(
    [
      JSON.stringify(
        {
          format: "querypilot-report-v1",
          exported_at: new Date().toISOString(),
          run,
        },
        null,
        2,
      ),
    ],
    { type: "application/json" },
  );
  const url = URL.createObjectURL(blob),
    anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `querypilot-${run.id}.json`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ComparisonSummary({ report }: { report: Report }) {
  const summary = report.summary;
  const max = Math.max(
    ...report.segments.map((s) => Math.abs(s.contribution)),
    1e-12,
  );
  return (
    <div className="comparison-report">
      <div className="section-heading">
        <div>
          <div className="eyebrow">RECONCILED PERIOD COMPARISON</div>
          <h3>{report.request.metric_id.replaceAll("_", " ")}</h3>
        </div>
        <span className="pill">
          {report.verified ? "Checks passed" : "Review required"}
        </span>
      </div>
      <p className="muted">
        {report.request.baseline.start} ≤ date &lt;{" "}
        {report.request.baseline.end}
        <br />
        versus {report.request.comparison.start} ≤ date &lt;{" "}
        {report.request.comparison.end}
      </p>
      {summary && (
        <>
          <div className="stats compact comparison-totals">
            <div>
              <span>Baseline · {summary.unit}</span>
              <strong>{number(summary.baseline)}</strong>
            </div>
            <div>
              <span>Comparison</span>
              <strong>{number(summary.comparison)}</strong>
            </div>
            <div>
              <span>Observed change</span>
              <strong>{number(summary.change, true)}</strong>
            </div>
            <div>
              <span>Relative change</span>
              <strong>
                {summary.relative_change == null
                  ? "Undefined"
                  : number(summary.relative_change * 100, true) + "%"}
              </strong>
            </div>
          </div>
          <h3>Contributions by {report.request.dimension}</h3>
          <p className="muted">
            {[
              "declined_referral_rate",
              "referral_wait",
              "coordination_cost",
            ].includes(report.request.metric_id)
              ? "Changes in each segment’s weighted contribution to the overall metric. Segment rate differences alone do not add to the overall change."
              : "Segment spend/count changes add to the observed total change."}
          </p>
          <div className="contribution-list">
            {report.segments.map((s) => (
              <div className="contribution-row" key={s.segment}>
                <div className="section-heading">
                  <strong>{s.segment}</strong>
                  <span>
                    {number(s.contribution, true)} {summary.unit}
                  </span>
                </div>
                <div className="contribution-track">
                  <div
                    className={s.contribution < 0 ? "negative" : "positive"}
                    style={{
                      width: `${(Math.abs(s.contribution) / max) * 100}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      {report.attribution && (
        <div className="factor-section">
          <h3>Claims change accounting</h3>
          {report.attribution.available ? (
            <>
              <p className="muted">
                Volume × {report.request.dimension} mix × unit cost. All six
                factor orders share interaction effects; these are descriptive
                accounting components.
              </p>
              <div className="factor-grid">
                {(["volume", "mix", "unit_cost"] as const).map((key) => (
                  <div key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>
                      {number(report.attribution?.[key], true)} USD
                    </strong>
                  </div>
                ))}
              </div>
              <small>
                Reconciliation residual: {number(report.attribution.residual)}{" "}
                USD
              </small>
            </>
          ) : (
            <p className="callout">{report.attribution.reason}</p>
          )}
        </div>
      )}
      <div className="callout">
        {report.source.resolution}. Latest warehouse date:{" "}
        {report.source.warehouse_latest || "No source data"}. Descriptive
        contributions do not establish causality.
      </div>
    </div>
  );
}

export function ComparisonChecks({ report }: { report: Report }) {
  return (
    <>
      <h2>Deterministic evidence checks</h2>
      <p className="muted">
        These checks execute in application code. A second model does not grade
        its own answer.
      </p>
      <div className="check-list">
        {report.checks.map((check) => (
          <div key={check.name} className="check-row">
            <span className="pill">{check.passed ? "PASS" : "REVIEW"}</span>
            <div>
              <strong>{check.name.replaceAll("_", " ")}</strong>
              <p className="muted">{check.detail}</p>
            </div>
          </div>
        ))}
      </div>
      <h3>Scope and limitations</h3>
      <ul>
        {report.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p className="muted">{report.source.transaction}</p>
      <pre>{JSON.stringify(report.request, null, 2)}</pre>
    </>
  );
}
