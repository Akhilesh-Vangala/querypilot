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
            table="fact_claims",
            sql="",
            chart="table",
            answer=(
                "Refused. QueryPilot only executes a single read-only SELECT "
                "(or WITH ... SELECT) against the warehouse."
            ),
            refused=True,
        )
    if "declined" in q and "specialty" in q:
        return Intent(
            id="declined_by_specialty",
            table="fact_referrals",
            chart="bar",
            answer="Declined-referral rate by specialty:",
            sql=(
                "SELECT p.specialty AS specialty, "
                "SUM(r.declined_referrals) * 1.0 / SUM(r.referrals) AS decline_rate "
                "FROM fact_referrals AS r "
                "INNER JOIN dim_provider AS p ON p.provider_id = r.provider_id "
                "GROUP BY p.specialty "
                "ORDER BY decline_rate DESC"
            ),
        )
    if "oncology" in q and "share" in q:
        return Intent(
            id="oncology_share",
            table="fact_claims",
            chart="table",
            answer="Oncology share of total claims paid:",
            sql=(
                "SELECT SUM(CASE WHEN p.specialty = 'Oncology' THEN c.claims_paid_usd ELSE 0 END) "
                "* 1.0 / SUM(c.claims_paid_usd) AS oncology_share "
                "FROM fact_claims AS c "
                "INNER JOIN dim_provider AS p ON p.provider_id = c.provider_id"
            ),
        )
    if "coordination" in q:
        return Intent(
            id="coordination_per_case",
            table="fact_care_coordination",
            chart="bar",
            answer="Average care-coordination cost per case by region and employer group:",
            sql=(
                "SELECT reg.region_code, emp.employer_code, "
                "SUM(cc.coordination_cost_usd) * 1.0 / SUM(cc.cases) AS cost_per_case "
                "FROM fact_care_coordination AS cc "
                "INNER JOIN dim_region AS reg ON reg.region_id = cc.region_id "
                "INNER JOIN dim_employer_group AS emp ON emp.employer_id = cc.employer_id "
                "GROUP BY reg.region_code, emp.employer_code "
                "ORDER BY reg.region_code, emp.employer_code"
            ),
        )
    if "panel" in q or "closed" in q:
        return Intent(
            id="closed_panel_employers",
            table="fact_network_capacity",
            chart="table",
            answer="Employer groups with at least one closed-panel week:",
            sql=(
                "SELECT emp.employer_code, emp.name "
                "FROM fact_network_capacity AS cap "
                "INNER JOIN dim_employer_group AS emp ON emp.employer_id = cap.employer_id "
                "WHERE cap.panel_closed_flag "
                "GROUP BY emp.employer_code, emp.name "
                "ORDER BY emp.employer_code"
            ),
        )
    if "q1" in q:
        return Intent(
            id="yoy_q1",
            table="fact_claims",
            chart="bar",
            answer="Q1 claims paid by year:",
            sql=(
                "SELECT dt.year AS year, SUM(c.claims_paid_usd) AS claims_paid "
                "FROM fact_claims AS c "
                "INNER JOIN dim_date AS dt ON dt.date_id = c.date_id "
                "WHERE dt.quarter = 1 "
                "GROUP BY dt.year "
                "ORDER BY dt.year"
            ),
        )
    if "month" in q and "highest" in q and "claims" in q:
        return Intent(
            id="peak_month",
            table="fact_claims",
            chart="bar",
            answer="Month with the highest claims paid:",
            sql=(
                "SELECT dt.year AS year, dt.month AS month, SUM(c.claims_paid_usd) AS claims_paid "
                "FROM fact_claims AS c "
                "INNER JOIN dim_date AS dt ON dt.date_id = c.date_id "
                "GROUP BY dt.year, dt.month "
                "ORDER BY claims_paid DESC "
                "LIMIT 1"
            ),
        )
    if "region" in q and "referrals" in q and "most" in q:
        return Intent(
            id="top_region_referrals",
            table="fact_referrals",
            chart="bar",
            answer="Region with the highest referral volume:",
            sql=(
                "SELECT reg.region_code, reg.name, SUM(r.referrals) AS referrals "
                "FROM fact_referrals AS r "
                "INNER JOIN dim_region AS reg ON reg.region_id = r.region_id "
                "GROUP BY reg.region_id, reg.region_code, reg.name "
                "ORDER BY referrals DESC "
                "LIMIT 1"
            ),
        )
    if "referred" in q and "claimed" in q:
        return Intent(
            id="referred_vs_claimed",
            table="fact_referrals",
            chart="bar",
            answer="Primary Care referrals versus claims by provider:",
            sql=(
                "SELECT prov.npi, "
                "COALESCE(ref.referrals, 0) AS referred, "
                "COALESCE(clm.claim_count, 0) AS claimed "
                "FROM dim_provider AS prov "
                "LEFT JOIN ("
                "  SELECT provider_id, SUM(referrals) AS referrals FROM fact_referrals GROUP BY provider_id"
                ") AS ref ON ref.provider_id = prov.provider_id "
                "LEFT JOIN ("
                "  SELECT provider_id, SUM(claim_count) AS claim_count FROM fact_claims GROUP BY provider_id"
                ") AS clm ON clm.provider_id = prov.provider_id "
                "WHERE prov.specialty = 'Primary Care' "
                "ORDER BY prov.npi"
            ),
        )
    if "top" in q and "5" in q:
        return Intent(
            id="top5_providers",
            table="fact_claims",
            chart="bar",
            answer="Top 5 providers by claims paid:",
            sql=(
                "SELECT p.npi, p.specialty, SUM(c.claims_paid_usd) AS claims_paid "
                "FROM fact_claims AS c "
                "INNER JOIN dim_provider AS p ON p.provider_id = c.provider_id "
                "GROUP BY p.provider_id, p.npi, p.specialty "
                "ORDER BY claims_paid DESC "
                "LIMIT 5"
            ),
        )
    if "claims" in q and "specialty" in q:
        return Intent(
            id="claims_by_specialty",
            table="fact_claims",
            chart="bar",
            answer="Claims paid by specialty:",
            sql=(
                "SELECT p.specialty AS specialty, SUM(c.claims_paid_usd) AS claims_paid "
                "FROM fact_claims AS c "
                "INNER JOIN dim_provider AS p ON p.provider_id = c.provider_id "
                "GROUP BY p.specialty "
                "ORDER BY claims_paid DESC"
            ),
        )
    if "total" in q and "claims" in q and "12" in q:
        return Intent(
            id="l12m_claims",
            table="fact_claims",
            chart="table",
            answer="Total claims paid over the last 52 weeks:",
            sql=(
                "SELECT SUM(c.claims_paid_usd) AS total_claims_paid "
                "FROM fact_claims AS c "
                "WHERE c.date_id > (SELECT MAX(dt.date_id) FROM dim_date AS dt) - 52"
            ),
        )
    return None
