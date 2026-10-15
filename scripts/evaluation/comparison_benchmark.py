"""Metric comparison regression across five query families; paid runs opt in."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from sqlalchemy.orm import Session
from app.persistence import db
from app.agents.analytics.llm import StubLLM
from app.agents.analytics.llm import get_llm
from app.agents.analytics.tools import WarehouseTools
from app.agents.analytics.workflow import AnalyticsWorkflow
from app.core.config import get_settings
from app.evaluation.comparisons import comparison_cases
from app.evaluation.comparisons import evaluate_comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["baseline", "live"], default="baseline")
    parser.add_argument("--case-limit", type=int, default=10)
    parser.add_argument("--ack-live-spend", action="store_true")
    parser.add_argument(
        "--output", default="artifacts/generated/comparison-benchmark.json"
    )
    args = parser.parse_args()
    if not 1 <= args.case_limit <= 10:
        parser.error("case-limit must be 1–10")
    settings = get_settings()
    if args.mode == "live" and (
        not args.ack_live_spend
        or not settings.openai_api_key
        or not settings.allow_live_ai
    ):
        parser.error(
            "Live evaluation requires private configuration and --ack-live-spend"
        )
    results = []
    with Session(db.engine) as session:
        tools = WarehouseTools(session)
        for case in comparison_cases()[: args.case_limit]:
            client = StubLLM() if args.mode == "baseline" else get_llm()
            try:
                result = AnalyticsWorkflow(session, client).run(case.question)
                passed = evaluate_comparison(result, case, tools)
                results.append(
                    {
                        "id": case.id,
                        "passed": passed,
                        "status": result["status"],
                        "rounds": result["rounds"],
                        "sql_attempts": result["attempts"],
                        "elapsed_ms": result["elapsed_ms"],
                        "usage": result["usage"],
                    }
                )
            except Exception as error:
                results.append(
                    {
                        "id": case.id,
                        "passed": False,
                        "error_kind": type(error).__name__,
                        "usage": getattr(client, "usage", {}),
                    }
                )
            finally:
                if hasattr(client, "close"):
                    client.close()
    report = {
        "suite": "reviewed-comparison-regression-v1",
        "mode": args.mode,
        "n": len(results),
        "passed": sum(r["passed"] for r in results),
        "metric_families": 5,
        "cases": results,
        "usage": {
            k: sum(r["usage"].get(k, 0) for r in results)
            for k in ("input_tokens", "output_tokens")
        },
        "median_latency_ms": statistics.median(r.get("elapsed_ms", 0) for r in results),
        "source_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("backend/app").rglob("*.py"))
        },
        "limitation": "Reviewed known templates over synthetic fixture, not held-out live-model accuracy. Independent unequal-data variants run in test_semantic.py. No causal interpretation is scored.",
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("cases", "source_sha256")}
        )
    )
    if report["passed"] != report["n"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
