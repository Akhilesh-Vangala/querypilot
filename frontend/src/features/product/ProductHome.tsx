import { Link } from "react-router-dom";
import { useProduct } from "./context";
import StudioIcon from "../../components/layout/StudioIcon";
export function Brand() {
  return (
    <Link to="/" className="brand" id="brand">
      <span className="brand-symbol" aria-hidden="true">
        q<span />
      </span>
      QueryPilot<span className="brand-edition">STUDIO</span>
    </Link>
  );
}
export default function ProductHome({ sample }: { sample: () => void }) {
  const ctx = useProduct();
  return (
    <div className="marketing studio-home">
      <header className="marketing-header">
        <Brand />
        <nav aria-label="Main navigation">
          <a href="#how-it-works">The workflow</a>
          <Link to="/demo">Investigation studio</Link>
          <Link className="primary" to="/workspace">
            Open workspace <StudioIcon name="arrow" />
          </Link>
        </nav>
      </header>
      <main className="marketing-main" id="main">
        <section className="studio-hero">
          <div className="studio-hero-copy">
            <span className="studio-kicker">
              <span /> A CLEARER WAY THROUGH YOUR DATA
            </span>
            <h1>
              Good questions.
              <br />
              <em>Verifiable answers.</em>
            </h1>
            <p className="lead">
              A space to explore the numbers, define what matters, and follow
              every answer back to its source.
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
            <p className="studio-formats">
              CSV <span>·</span> TSV <span>·</span> Excel <span>·</span> JSON{" "}
              <span>·</span> JSONL
            </p>
            <p className="hint">
              No account needed. Save only when you choose.
            </p>
          </div>
          <div
            className="studio-canvas"
            aria-label="Illustrative calculation: 0.10 plus 0.20 equals 0.30, checked independently"
          >
            <div className="canvas-heading">
              <span className="canvas-dots">
                <i />
                <i />
                <i />
              </span>
              <span>THE EVIDENCE DESK</span>
              <StudioIcon name="data" />
            </div>
            <div className="canvas-question">
              <span className="canvas-avatar">Q</span>
              <div>
                <small>YOUR QUESTION</small>
                <p>What is our total for completed records?</p>
              </div>
            </div>
            <div className="canvas-columns">
              <div className="canvas-source">
                <span className="eyebrow">01 / SOURCE</span>
                <div className="mini-table">
                  <div>
                    <b>region</b>
                    <b>amount</b>
                  </div>
                  <div>
                    <span>North</span>
                    <span>0.10</span>
                  </div>
                  <div>
                    <span>North</span>
                    <span>0.20</span>
                  </div>
                  <div className="excluded">
                    <span>South</span>
                    <span>5.00</span>
                  </div>
                </div>
                <small>
                  Filter: status = done
                  <br />
                  Illustrative data · 2 included rows
                </small>
              </div>
              <div className="canvas-result">
                <span className="eyebrow">02 / CHECKED RESULT</span>
                <strong>0.30</strong>
                <div className="sample-bars" aria-hidden="true">
                  <i />
                  <i />
                </div>
                <span className="canvas-verified">
                  <StudioIcon name="check" /> SQL = Decimal reference
                </span>
              </div>
            </div>
            <div className="canvas-code">
              <span>03 / EXECUTION</span>
              <code>SUM(amount) WHERE status = 'done'</code>
              <span className="canvas-caption">
                Illustrative expression · inspect executed SQL in your report
              </span>
            </div>
            <div className="canvas-footer">
              <span className="canvas-label">
                SOURCE → DEFINITION → EVIDENCE
              </span>
              <span>Every step, inspectable.</span>
            </div>
          </div>
        </section>
        <section
          className="studio-paths"
          aria-label="Choose an analytical workflow"
        >
          <Link className="path-card path-upload" to="/uploads?new=1">
            <span className="path-icon">
              <StudioIcon name="upload" />
            </span>
            <div>
              <span className="eyebrow">YOUR FILES</span>
              <h2>From export to insight.</h2>
              <p>Profile a table, review a metric, and reconcile the result.</p>
            </div>
            <StudioIcon name="arrow" />
          </Link>
          <Link className="path-card path-investigate" to="/demo">
            <span className="path-icon">
              <StudioIcon name="query" />
            </span>
            <div>
              <span className="eyebrow">WAREHOUSE STUDIO</span>
              <h2>Follow the analytical trail.</h2>
              <p>
                Explore claims and provider metrics with a guided investigator.
              </p>
            </div>
            <StudioIcon name="arrow" />
          </Link>
        </section>
        <section className="studio-method" id="how-it-works">
          <div className="method-intro">
            <span className="eyebrow">THE WORKFLOW</span>
            <h2>
              The answer is only
              <br />
              half the story.
            </h2>
            <p>
              The definition, calculation and independent checks travel with
              every report.
            </p>
            <Link className="text-link" to="/workspace/guide">
              Explore the guide →
            </Link>
          </div>
          <div className="method-steps">
            {[
              [
                "01",
                "Bring the source.",
                "Preview actual records and inspect missing values before choosing what to measure.",
                "data",
              ],
              [
                "02",
                "Make the rules explicit.",
                "Select a sum, count or weighted overall average. Review grouping and exact-match filters.",
                "settings",
              ],
              [
                "03",
                "Inspect the evidence.",
                "Reconcile executed SQL with a separate Decimal computation. Keep exact values and export the report.",
                "check",
              ],
            ].map(([n, h, p, icon]) => (
              <article key={n}>
                <span className="method-number">{n}</span>
                <div>
                  <h3>{h}</h3>
                  <p>{p}</p>
                </div>
                <StudioIcon name={icon} />
              </article>
            ))}
          </div>
        </section>
        <section className="studio-bottom">
          <div>
            <span className="eyebrow">
              A WORKSPACE THAT REMEMBERS WHAT YOU KEEP
            </span>
            <h2>
              Less spreadsheet guesswork.
              <br />
              More context with every number.
            </h2>
            <p>
              Organize projects, keep immutable device snapshots, and transfer
              validated backups between browsers.
            </p>
          </div>
          <div className="studio-bottom-actions">
            <Link className="primary" to="/uploads?new=1">
              Start an analysis →
            </Link>
            <span>
              Public analysis uses reviewed rules.
              <br />
              Warehouse exploration uses a guided baseline.
            </span>
          </div>
        </section>
        <footer className="marketing-footer">
          <Brand />
          <span>Questions. Definitions. Executed evidence.</span>
          <div className="actions">
            <Link to="/workspace/settings">Data handling</Link>
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
