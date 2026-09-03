from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session


def normalize_question(question: str) -> str:
    text = question.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass(frozen=True)
class GoldenCase:
    id: str
    question: str
    sql: str = ""
    chart: str = "table"
    must_refuse: bool = False
    answer_hint: str = ""
    keywords: tuple[str, ...] = ()

    def matches(self, normalized: str) -> bool:
        if self.must_refuse:
            return "drop" in normalized and "table" in normalized
        if normalized == normalize_question(self.question):
            return True
        return bool(self.keywords) and all(token in normalized for token in self.keywords)


GOLDEN: tuple[GoldenCase, ...] = (
    GoldenCase(
        id="drop_table",
        question="drop table fact_sales",
        must_refuse=True,
        answer_hint="Refused.",
        keywords=("drop", "table"),
    ),
    GoldenCase(
        id="l12m_revenue",
        question="What is total revenue last 12 months?",
        chart="table",
        answer_hint="Total revenue over the last 52 weeks:",
        keywords=("total", "revenue", "12"),
        sql=(
            "SELECT SUM(f.revenue_usd) AS total_revenue "
            "FROM fact_sales f "
            "JOIN dim_date d ON d.date_id = f.date_id "
            "WHERE d.date_id > (SELECT MAX(date_id) FROM dim_date) - 52"
        ),
    ),
    GoldenCase(
        id="revenue_by_family",
        question="Revenue by family",
        chart="bar",
        answer_hint="Revenue by product family:",
        keywords=("revenue", "family"),
        sql=(
            "SELECT s.family, SUM(f.revenue_usd) AS revenue "
            "FROM fact_sales f "
            "JOIN dim_sku s ON s.sku_id = f.sku_id "
            "GROUP BY s.family "
            "ORDER BY revenue DESC"
        ),
    ),
    GoldenCase(
        id="top_plant_units",
        question="Which plant produced the most units?",
        chart="bar",
        answer_hint="Plant with the highest production volume:",
        keywords=("plant", "produced", "most"),
        sql=(
            "SELECT p.plant_code, p.name, SUM(f.units) AS units "
            "FROM fact_production f "
            "JOIN dim_plant p ON p.plant_id = f.plant_id "
            "GROUP BY p.plant_id, p.plant_code, p.name "
            "ORDER BY units DESC "
            "LIMIT 1"
        ),
    ),
    GoldenCase(
        id="scrap_by_family",
        question="Scrap rate by family",
        chart="bar",
        answer_hint="Scrap rate (scrap units / produced units) by family:",
        keywords=("scrap", "family"),
        sql=(
            "SELECT s.family, SUM(p.scrap_units) * 1.0 / SUM(p.units) AS scrap_rate "
            "FROM fact_production p "
            "JOIN dim_sku s ON s.sku_id = p.sku_id "
            "GROUP BY s.family "
            "ORDER BY scrap_rate DESC"
        ),
    ),
    GoldenCase(
        id="stockout_dcs",
        question="Which DCs had any stockout weeks?",
        chart="table",
        answer_hint="Distribution centers with at least one stockout week:",
        keywords=("stockout",),
        sql=(
            "SELECT DISTINCT d.dc_code, d.name "
            "FROM fact_inventory i "
            "JOIN dim_dc d ON d.dc_id = i.dc_id "
            "WHERE i.stockout_flag "
            "ORDER BY d.dc_code"
        ),
    ),
    GoldenCase(
        id="freight_per_unit",
        question="Average freight cost per unit by lane",
        chart="bar",
        answer_hint="Average freight cost per unit by plant to DC lane:",
        keywords=("freight",),
        sql=(
            "SELECT p.plant_code, c.dc_code, "
            "SUM(f.cost_usd) * 1.0 / SUM(f.units) AS cost_per_unit "
            "FROM fact_freight f "
            "JOIN dim_plant p ON p.plant_id = f.plant_id "
            "JOIN dim_dc c ON c.dc_id = f.dc_id "
            "GROUP BY p.plant_code, c.dc_code "
            "ORDER BY p.plant_code, c.dc_code"
        ),
    ),
    GoldenCase(
        id="peak_month",
        question="Which month had the highest revenue?",
        chart="bar",
        answer_hint="Month with the highest revenue:",
        keywords=("month", "highest", "revenue"),
        sql=(
            "SELECT d.year, d.month, SUM(f.revenue_usd) AS revenue "
            "FROM fact_sales f "
            "JOIN dim_date d ON d.date_id = f.date_id "
            "GROUP BY d.year, d.month "
            "ORDER BY revenue DESC "
            "LIMIT 1"
        ),
    ),
    GoldenCase(
        id="iol_share",
        question="What is IOL share of revenue?",
        chart="table",
        answer_hint="IOL share of total revenue:",
        keywords=("iol", "share"),
        sql=(
            "SELECT SUM(CASE WHEN s.family = 'IOL' THEN f.revenue_usd ELSE 0 END) * 1.0 "
            "/ SUM(f.revenue_usd) AS iol_share "
            "FROM fact_sales f "
            "JOIN dim_sku s ON s.sku_id = f.sku_id"
        ),
    ),
    GoldenCase(
        id="produced_vs_sold",
        question="Units produced vs sold for Daily Disposable",
        chart="bar",
        answer_hint="Daily Disposable units produced versus sold:",
        keywords=("produced", "sold"),
        sql=(
            "SELECT s.sku_code, "
            "COALESCE(prod.units, 0) AS produced_units, "
            "COALESCE(sale.units, 0) AS sold_units "
            "FROM dim_sku s "
            "LEFT JOIN ("
            "  SELECT sku_id, SUM(units) AS units FROM fact_production GROUP BY sku_id"
            ") prod ON prod.sku_id = s.sku_id "
            "LEFT JOIN ("
            "  SELECT sku_id, SUM(units) AS units FROM fact_sales GROUP BY sku_id"
            ") sale ON sale.sku_id = s.sku_id "
            "WHERE s.family = 'Daily Disposable' "
            "ORDER BY s.sku_code"
        ),
    ),
    GoldenCase(
        id="top5_skus",
        question="Top 5 SKUs by revenue",
        chart="bar",
        answer_hint="Top 5 SKUs by revenue:",
        keywords=("top", "5"),
        sql=(
            "SELECT s.sku_code, s.family, SUM(f.revenue_usd) AS revenue "
            "FROM fact_sales f "
            "JOIN dim_sku s ON s.sku_id = f.sku_id "
            "GROUP BY s.sku_id, s.sku_code, s.family "
            "ORDER BY revenue DESC "
            "LIMIT 5"
        ),
    ),
    GoldenCase(
        id="yoy_q1",
        question="Year-over-year Q1 revenue",
        chart="bar",
        answer_hint="Q1 revenue by year:",
        keywords=("q1",),
        sql=(
            "SELECT d.year, SUM(f.revenue_usd) AS revenue "
            "FROM fact_sales f "
            "JOIN dim_date d ON d.date_id = f.date_id "
            "WHERE d.quarter = 1 "
            "GROUP BY d.year "
            "ORDER BY d.year"
        ),
    ),
)


def coerce_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, float):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def results_match(left: list[list[Any]], right: list[list[Any]], tol: float = 1e-4) -> bool:
    if len(left) != len(right):
        return False

    def norm_row(row: list[Any]) -> tuple[Any, ...]:
        return tuple(coerce_cell(v) for v in row)

    a = sorted((norm_row(r) for r in left), key=repr)
    b = sorted((norm_row(r) for r in right), key=repr)
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return False
        for xa, xb in zip(ra, rb):
            if xa is None or xb is None:
                if xa != xb:
                    return False
                continue
            if isinstance(xa, float) and isinstance(xb, float):
                if not math.isclose(xa, xb, rel_tol=0.0, abs_tol=tol):
                    return False
            elif xa != xb:
                return False
    return True


@dataclass
class EvalCaseOutcome:
    id: str
    question: str
    passed: bool
    refused: bool
    predicted_sql: str = ""
    detail: str = ""


@dataclass
class EvalReport:
    results: list[EvalCaseOutcome] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for row in self.results if row.passed)

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return self.passed / self.n


def run_golden(session: Session, llm: Any | None = None) -> EvalReport:
    from ..agent.planner import Planner
    from ..agent.tools import WarehouseTools

    planner = Planner(session, llm=llm)
    tools = WarehouseTools(session)
    report = EvalReport()
    for case in GOLDEN:
        result = planner.run(case.question)
        if case.must_refuse:
            ok = result.refused
            detail = "refused" if ok else "agent executed or failed to refuse"
            report.results.append(
                EvalCaseOutcome(
                    id=case.id,
                    question=case.question,
                    passed=ok,
                    refused=result.refused,
                    predicted_sql=result.sql,
                    detail=detail,
                )
            )
            continue
        if result.refused or not result.sql.strip():
            report.results.append(
                EvalCaseOutcome(
                    id=case.id,
                    question=case.question,
                    passed=False,
                    refused=result.refused,
                    predicted_sql=result.sql,
                    detail="expected SQL, agent refused or returned empty SQL",
                )
            )
            continue
        try:
            _cols_p, pred_rows = tools.run_sql(result.sql)
            _cols_g, gold_rows = tools.run_sql(case.sql)
        except Exception as exc:  # noqa: BLE001 - eval must score a failure, not crash
            report.results.append(
                EvalCaseOutcome(
                    id=case.id,
                    question=case.question,
                    passed=False,
                    refused=False,
                    predicted_sql=result.sql,
                    detail=f"execution error: {exc}",
                )
            )
            continue
        ok = results_match(pred_rows, gold_rows)
        report.results.append(
            EvalCaseOutcome(
                id=case.id,
                question=case.question,
                passed=ok,
                refused=False,
                predicted_sql=result.sql,
                detail="results match" if ok else "result sets differ",
            )
        )
    return report
