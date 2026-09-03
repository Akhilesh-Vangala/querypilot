"""Intent-to-SQL compiler used by StubLLM. Independent of eval/golden.py."""

from __future__ import annotations

from dataclasses import dataclass

from ..eval.golden import normalize_question


@dataclass(frozen=True)
class Intent:
    id: str
    table: str
    sql: str
    chart: str
    answer: str
    refused: bool = False


def classify(question: str) -> Intent | None:
    q = normalize_question(question)

    if "drop" in q and "table" in q:
        return Intent(
            id="drop_table",
            table="fact_sales",
            sql="",
            chart="table",
            answer=(
                "Refused. QueryPilot only executes a single read-only SELECT "
                "(or WITH ... SELECT) against the warehouse."
            ),
            refused=True,
        )
    if "scrap" in q and "family" in q:
        return Intent(
            id="scrap_by_family",
            table="fact_production",
            chart="bar",
            answer="Scrap rate by family:",
            sql=(
                "SELECT sku.family AS family, "
                "SUM(prod.scrap_units) * 1.0 / SUM(prod.units) AS scrap_rate "
                "FROM fact_production AS prod "
                "INNER JOIN dim_sku AS sku ON sku.sku_id = prod.sku_id "
                "GROUP BY sku.family "
                "ORDER BY scrap_rate DESC"
            ),
        )
    if "iol" in q and "share" in q:
        return Intent(
            id="iol_share",
            table="fact_sales",
            chart="table",
            answer="IOL share of total revenue:",
            sql=(
                "SELECT SUM(CASE WHEN sku.family = 'IOL' THEN sale.revenue_usd ELSE 0 END) "
                "* 1.0 / SUM(sale.revenue_usd) AS iol_share "
                "FROM fact_sales AS sale "
                "INNER JOIN dim_sku AS sku ON sku.sku_id = sale.sku_id"
            ),
        )
    if "freight" in q:
        return Intent(
            id="freight_per_unit",
            table="fact_freight",
            chart="bar",
            answer="Average freight cost per unit by plant to DC lane:",
            sql=(
                "SELECT plant.plant_code, dc.dc_code, "
                "SUM(fr.cost_usd) * 1.0 / SUM(fr.units) AS cost_per_unit "
                "FROM fact_freight AS fr "
                "INNER JOIN dim_plant AS plant ON plant.plant_id = fr.plant_id "
                "INNER JOIN dim_dc AS dc ON dc.dc_id = fr.dc_id "
                "GROUP BY plant.plant_code, dc.dc_code "
                "ORDER BY plant.plant_code, dc.dc_code"
            ),
        )
    if "stockout" in q:
        return Intent(
            id="stockout_dcs",
            table="fact_inventory",
            chart="table",
            answer="Distribution centers with at least one stockout week:",
            sql=(
                "SELECT dc.dc_code, dc.name "
                "FROM fact_inventory AS inv "
                "INNER JOIN dim_dc AS dc ON dc.dc_id = inv.dc_id "
                "WHERE inv.stockout_flag "
                "GROUP BY dc.dc_code, dc.name "
                "ORDER BY dc.dc_code"
            ),
        )
    if "q1" in q:
        return Intent(
            id="yoy_q1",
            table="fact_sales",
            chart="bar",
            answer="Q1 revenue by year:",
            sql=(
                "SELECT dt.year AS year, SUM(sale.revenue_usd) AS revenue "
                "FROM fact_sales AS sale "
                "INNER JOIN dim_date AS dt ON dt.date_id = sale.date_id "
                "WHERE dt.quarter = 1 "
                "GROUP BY dt.year "
                "ORDER BY dt.year"
            ),
        )
    if "month" in q and "highest" in q and "revenue" in q:
        return Intent(
            id="peak_month",
            table="fact_sales",
            chart="bar",
            answer="Month with the highest revenue:",
            sql=(
                "SELECT dt.year AS year, dt.month AS month, SUM(sale.revenue_usd) AS revenue "
                "FROM fact_sales AS sale "
                "INNER JOIN dim_date AS dt ON dt.date_id = sale.date_id "
                "GROUP BY dt.year, dt.month "
                "ORDER BY revenue DESC "
                "LIMIT 1"
            ),
        )
    if "plant" in q and "produced" in q and "most" in q:
        return Intent(
            id="top_plant_units",
            table="fact_production",
            chart="bar",
            answer="Plant with the highest production volume:",
            sql=(
                "SELECT plant.plant_code, plant.name, SUM(prod.units) AS units "
                "FROM fact_production AS prod "
                "INNER JOIN dim_plant AS plant ON plant.plant_id = prod.plant_id "
                "GROUP BY plant.plant_id, plant.plant_code, plant.name "
                "ORDER BY units DESC "
                "LIMIT 1"
            ),
        )
    if "produced" in q and "sold" in q:
        return Intent(
            id="produced_vs_sold",
            table="fact_production",
            chart="bar",
            answer="Daily Disposable units produced versus sold:",
            sql=(
                "SELECT sku.sku_code, "
                "COALESCE(made.units, 0) AS produced_units, "
                "COALESCE(sold.units, 0) AS sold_units "
                "FROM dim_sku AS sku "
                "LEFT JOIN ("
                "  SELECT sku_id, SUM(units) AS units FROM fact_production GROUP BY sku_id"
                ") AS made ON made.sku_id = sku.sku_id "
                "LEFT JOIN ("
                "  SELECT sku_id, SUM(units) AS units FROM fact_sales GROUP BY sku_id"
                ") AS sold ON sold.sku_id = sku.sku_id "
                "WHERE sku.family = 'Daily Disposable' "
                "ORDER BY sku.sku_code"
            ),
        )
    if "top" in q and "5" in q:
        return Intent(
            id="top5_skus",
            table="fact_sales",
            chart="bar",
            answer="Top 5 SKUs by revenue:",
            sql=(
                "SELECT sku.sku_code, sku.family, SUM(sale.revenue_usd) AS revenue "
                "FROM fact_sales AS sale "
                "INNER JOIN dim_sku AS sku ON sku.sku_id = sale.sku_id "
                "GROUP BY sku.sku_id, sku.sku_code, sku.family "
                "ORDER BY revenue DESC "
                "LIMIT 5"
            ),
        )
    if "revenue" in q and "family" in q:
        return Intent(
            id="revenue_by_family",
            table="fact_sales",
            chart="bar",
            answer="Revenue by product family:",
            sql=(
                "SELECT sku.family AS family, SUM(sale.revenue_usd) AS revenue "
                "FROM fact_sales AS sale "
                "INNER JOIN dim_sku AS sku ON sku.sku_id = sale.sku_id "
                "GROUP BY sku.family "
                "ORDER BY revenue DESC"
            ),
        )
    if "total" in q and "revenue" in q and "12" in q:
        return Intent(
            id="l12m_revenue",
            table="fact_sales",
            chart="table",
            answer="Total revenue over the last 52 weeks:",
            sql=(
                "SELECT SUM(sale.revenue_usd) AS total_revenue "
                "FROM fact_sales AS sale "
                "WHERE sale.date_id > (SELECT MAX(dt.date_id) FROM dim_date AS dt) - 52"
            ),
        )
    return None
