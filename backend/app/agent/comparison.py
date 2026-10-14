"""Inspectable LangGraph subworkflow: compile → execute → reconcile → publish."""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from .catalog import CONTRACT
from .semantic import (
    ComparisonRequest,
    compile_comparison,
    verify_comparison,
    receipt_digest,
    VERSION,
)


class ComparisonState(TypedDict, total=False):
    sql: str
    columns: list
    rows: list
    query: dict
    report: dict
    result: dict


class ComparisonWorkflow:
    def __init__(self, tools, request: ComparisonRequest, event):
        self.tools, self.request, self.event = tools, request, event

    def run(self):
        request = self.request
        plan = {
            "objective": f"Compare {request.metric_id} by {request.dimension}",
            "metric_ids": [request.metric_id],
            "assumptions": [
                "Half-open calendar windows over weekly snapshots",
                CONTRACT["no_causal_claims"],
                "Dimension and denominator are bound to an executable metric contract",
            ],
            "checks": [
                "Same-statement totals and segments",
                "Period coverage and input quality",
                "Numerator/denominator reconciliation",
                "Contribution accounting",
            ],
        }
        self.event("analysis_plan", plan=plan, origin="executable contract")

        def compile_node(_):
            dialect = (
                "postgres"
                if self.tools._engine().dialect.name == "postgresql"
                else "sqlite"
            )
            sql = compile_comparison(request, dialect)
            self.event(
                "compile_metric_contract", version=VERSION, metric=request.metric_id
            )
            return {"sql": sql}

        def execute_node(state):
            columns, rows = self.tools.run_sql(state["sql"])
            self.event("execute_comparison", rows=len(rows), statement_count=1)
            return {"columns": columns, "rows": rows, "query": self.tools.last_query}

        def verify_node(state):
            report = verify_comparison(
                request, state["columns"], state["rows"], state["query"]
            )
            self.event(
                "reconcile_metric_evidence",
                "complete" if report["verified"] else "attention",
                passed=sum(c["passed"] for c in report["checks"]),
                total=len(report["checks"]),
            )
            return {"report": report}

        def report_node(state):
            report = state["report"]
            summary = report["summary"]
            if report["verified"]:
                answer = f"{request.metric_id}: {summary['baseline']:,.4f} → {summary['comparison']:,.4f} {summary['unit']}; change {summary['change']:+,.4f}. Descriptive contributions reconcile; this does not establish causality."
                columns = [request.dimension, "baseline", "comparison", "contribution"]
                rows = [
                    [r["segment"], r["baseline"], r["comparison"], r["contribution"]]
                    for r in report["segments"]
                ]
            else:
                failed = ", ".join(
                    c["name"] for c in report["checks"] if not c["passed"]
                )
                answer = (
                    "Comparison withheld: "
                    + failed
                    + ". Review the requested dates, filters and source quality."
                )
                columns, rows = [], []
            digest = receipt_digest(request, state["columns"], state["rows"])
            self.event(
                "publish_comparison_report",
                "complete" if report["verified"] else "attention",
                result_sha256=digest,
            )
            return {
                "result": {
                    "answer": answer,
                    "sql": state["sql"],
                    "chart": "table",
                    "columns": columns,
                    "rows": rows,
                    "refused": False,
                    "status": "completed"
                    if report["verified"]
                    else "needs_clarification",
                    "plan": plan,
                    "comparison": report,
                    "validation": {
                        **state["query"],
                        "executed": True,
                        "result_sha256": digest,
                        "semantic_guarantee": "Executable metric contract, data-quality/coverage and arithmetic reconciliation checked; model intent and causality are not proven",
                    },
                    "evidence": {
                        "version": VERSION,
                        "request": request.model_dump(),
                        "columns": state["columns"],
                        "rows": state["rows"],
                        "result_sha256": digest,
                    },
                }
            }

        graph = StateGraph(ComparisonState)
        for name, node in (
            ("compile_metric", compile_node),
            ("execute_snapshot", execute_node),
            ("verify_accounting", verify_node),
            ("publish_report", report_node),
        ):
            graph.add_node(name, node)
        graph.add_edge(START, "compile_metric")
        graph.add_edge("compile_metric", "execute_snapshot")
        graph.add_edge("execute_snapshot", "verify_accounting")
        graph.add_edge("verify_accounting", "publish_report")
        graph.add_edge("publish_report", END)
        return graph.compile().invoke({})["result"]
