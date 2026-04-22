import { Link } from "react-router-dom";
import { useProduct } from "./context";
export function Brand() {
  return (
    <Link to="/" className="brand" id="brand">
      <span className="brand-symbol" aria-hidden="true">
        Q
      </span>
      QueryPilot
    </Link>
  );
}
export default function ProductHome({ sample }: { sample: () => void }) {
  const ctx = useProduct();
  return (
    <div className="marketing">
      <header className="marketing-header">
        <Brand />
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link to="/workspace/guide">Documentation</Link>
          <Link className="primary" to="/workspace">
            Open workspace
          </Link>
        </nav>
      </header>
      <main className="marketing-main" id="main">
        <section className="marketing-hero">
          <div>
            <span className="badge">ANALYTICS, WITH EXECUTED EVIDENCE</span>
            <h1>
              Ask a precise question.
              <br />
              Keep the evidence.
            </h1>
            <p className="lead">
              Bring your data. Review the metric and filter, inspect the
              executed SQL, and get a result independently reconciled from the
              source.
            </p>
            <div className="actions">
              <Link className="primary" to="/uploads?new=1">
                Analyze your data →
              </Link>
              <button
                className="secondary"
                onClick={sample}
                disabled={ctx.busy}
              >
                Try a sample file
              </button>
            </div>
            <p className="hint spaced">
              Start without an account. Saving is an explicit choice.
            </p>
          </div>
          <div
            className="hero-proof"
            aria-label="Illustrative result from the downloadable sample file"
          >
            <div className="proof-top">
              <span>REVENUE BY REGION</span>
              <span className="badge">Sample report</span>
            </div>
            <div className="proof-body">
              <p className="eyebrow">THE CHECKED SUM</p>
              <strong className="proof-amount">265.50</strong>
              <p className="hint spaced">
                4 included source records · 2 groups · No filter
              </p>
              {[
                "A reviewed measure and grouping",
                "SQL sums and counts independently reconciled",
                "Exact decimal strings preserved in exports",
              ].map((t) => (
                <div className="proof-line" key={t}>
                  ✓ {t}
                </div>
              ))}
            </div>
            <div className="proof-footer">
              Descriptive analytics under explicit rules. No invented causal
              explanation.
            </div>
          </div>
        </section>
        <div className="marketing-divider">
          <span>Reviewed metric contracts</span>
          <span>Independent Decimal reference</span>
          <span>Read-only source processing</span>
        </div>
        <section className="marketing-section" id="how-it-works">
          <p className="eyebrow">FROM QUESTION TO AN INSPECTABLE ANSWER</p>
          <h2>Make the definition part of the result.</h2>
          <div className="marketing-steps">
            {[
              [
                "01 / INSPECT",
                "Start with your export.",
                "Preview actual rows, inspect missing values and numeric coverage, and find the records behind an error.",
              ],
              [
                "02 / DEFINE",
                "Say what should count.",
                "Choose sum, count or average. Review the measure, grouping and exact-match filter before executing.",
              ],
              [
                "03 / VERIFY",
                "Keep an answer you can inspect.",
                "Compare the SQL output with a separate Decimal reference, inspect exact group values and export evidence.",
              ],
            ].map(([n, h, p]) => (
              <article key={n}>
                <span className="step-label">{n}</span>
                <h3>{h}</h3>
                <p>{p}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="marketing-section">
          <p className="eyebrow">RECOVERABLE WORK</p>
          <h2>Keep context when you come back.</h2>
          <p>
            Save deliberate device snapshots, organize projects and transfer a
            validated backup to another browser. Public own-data analysis uses
            reviewed contracts; live language interpretation remains
            unavailable.
          </p>
        </section>
        <section className="marketing-cta">
          <div>
            <h2>Bring the question behind the spreadsheet.</h2>
            <p>Use data you are authorized to share.</p>
          </div>
          <Link className="primary" to="/uploads?new=1">
            Start an analysis →
          </Link>
        </section>
        <footer className="marketing-footer">
          <span>QueryPilot · Questions to executed evidence</span>
          <div className="actions">
            <Link to="/workspace/settings">Data handling</Link>
            <Link to="/demo">Guided analytics demo</Link>
            <a
              href="https://github.com/Akhilesh-Vangala/querypilot"
              target="_blank"
              rel="noreferrer"
            >
              GitHub ↗
            </a>
          </div>
        </footer>
      </main>
    </div>
  );
}
