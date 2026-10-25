import { useId, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import StudioIcon from "../../components/layout/StudioIcon";
import { STARTERS, investigationLink } from "./questions";

export default function PromptComposer({
  surface = "warehouse",
}: {
  surface?: "landing" | "warehouse";
}) {
  const [question, setQuestion] = useState("");
  const navigate = useNavigate(),
    id = useId();
  function submit(e: FormEvent) {
    e.preventDefault();
    if (question.trim()) navigate(investigationLink(question.trim()));
  }
  return (
    <section
      className={`query-composer composer-${surface}`}
      aria-label="Warehouse question composer"
    >
      <div className="composer-heading">
        <span className="composer-symbol" aria-hidden="true">
          <StudioIcon name="query" />
        </span>
        <div>
          <span className="composer-eyebrow">THE INVESTIGATION DESK</span>
          <h2>What would you like to understand?</h2>
        </div>
        <span className="composer-mode">Guided entry points</span>
      </div>
      <form onSubmit={submit}>
        <label htmlFor={id}>Ask the warehouse</label>
        <textarea
          id={id}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What explains the change in claims paid between Q1 and Q2 2026?"
          maxLength={4000}
          rows={2}
          required
        />
        <div className="composer-toolbar">
          <span>
            <StudioIcon name="data" /> Synthetic claims & provider data
          </span>
          <button type="submit" disabled={!question.trim()}>
            Review question <StudioIcon name="arrow" />
          </button>
        </div>
      </form>
      <div
        className="composer-starters"
        aria-label="Suggested analytical questions"
      >
        {STARTERS.map((s) => (
          <button key={s.label} onClick={() => setQuestion(s.question)}>
            <StudioIcon name={s.icon} />
            {s.label}
            <span>↗</span>
          </button>
        ))}
      </div>
      <p className="composer-scope">
        Review the question and investigator before running. Public exploration
        uses a deterministic guided investigator.{" "}
        <Link to="/uploads">Analyze your own file →</Link>
      </p>
    </section>
  );
}
