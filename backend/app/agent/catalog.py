"""Reviewed semantic contracts exposed to the agent; evaluation answers stay separate."""

WAREHOUSE_TABLES = (
    "dim_provider",
    "dim_region",
    "dim_employer_group",
    "dim_date",
    "fact_claims",
    "fact_referrals",
    "fact_network_capacity",
    "fact_care_coordination",
)
METRICS = [
    {
        "id": "claims_paid",
        "name": "Claims paid",
        "unit": "USD",
        "table": "fact_claims",
        "grain": "week × provider × employer",
        "expression": "SUM(claims_paid_usd)",
        "definition": "Paid claims in the synthetic warehouse; amounts are additive at the recorded grain.",
    },
    {
        "id": "declined_referral_rate",
        "name": "Declined referral rate",
        "unit": "ratio",
        "table": "fact_referrals",
        "grain": "week × provider × region",
        "expression": "SUM(declined_referrals) / NULLIF(SUM(referrals), 0)",
        "definition": "Volume-weighted decline rate. Do not average provider rates without their denominators.",
    },
    {
        "id": "referral_wait",
        "name": "Referral wait",
        "unit": "days",
        "table": "fact_referrals",
        "grain": "week × provider × region",
        "expression": "SUM(avg_wait_days * referrals) / NULLIF(SUM(referrals), 0)",
        "definition": "Referral-weighted wait time. Raw average wait is a different metric.",
    },
    {
        "id": "closed_panels",
        "name": "Closed panels",
        "unit": "provider-weeks",
        "table": "fact_network_capacity",
        "grain": "week × provider × employer",
        "expression": "SUM(CASE WHEN panel_closed_flag THEN 1 ELSE 0 END)",
        "definition": "Counts records with closed panels, not distinct members or patient outcomes.",
    },
    {
        "id": "coordination_cost",
        "name": "Coordination cost per case",
        "unit": "USD/case",
        "table": "fact_care_coordination",
        "grain": "week × region × employer",
        "expression": "SUM(coordination_cost_usd) / NULLIF(SUM(cases), 0)",
        "definition": "Case-volume-weighted cost; total spend divided by total cases.",
    },
]
CONTRACT = {
    "version": "claims-network-v2",
    "data": "Original synthetic claims/provider-network fixture",
    "time_anchor": "Latest dim_date.date; weekly snapshots, not current wall-clock date",
    "last_12_months": "Legacy development benchmark uses the latest 52 weekly records; state this approximation explicitly.",
    "join_rule": "Join facts to their dimensions. Aggregate separate facts to a common grain before joining them.",
    "no_causal_claims": "Observed associations do not establish causes or patient-level outcomes.",
}
