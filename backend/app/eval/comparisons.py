"""Reviewed comparison regression oracles, never imported into agent context."""

from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True)
class ComparisonCase:
    metric: str
    dimension: str
    name: str
    source: str
    numerator: str
    denominator: str
    joins: str
    grouping: str
    ratio: bool

    @property
    def id(self):
        return self.metric + "-" + self.dimension

    @property
    def question(self):
        return f"Compare {self.name} from 2026-01-01 to 2026-04-01 versus 2026-04-01 to 2026-07-01 by {self.dimension}"

    @property
    def gold_sql(self):
        # Independently authored quarterly query; compiler uses half-open dates,
        # CTE total/segment branches, quality counters and coverage metadata.
        return f"SELECT d.quarter, {self.grouping} AS segment, SUM({self.numerator}) AS numerator, SUM({self.denominator}) AS denominator FROM {self.source} f JOIN dim_date d ON d.date_id=f.date_id {self.joins} WHERE d.year=2026 AND d.quarter IN (1,2) GROUP BY d.quarter, {self.grouping} ORDER BY d.quarter, {self.grouping}"


def comparison_cases():
    cases = []
    metrics = [
        (
            "claims_paid",
            "claims paid",
            "fact_claims",
            "f.claims_paid_usd",
            "f.claim_count",
            False,
            ("specialty", "employer"),
        ),
        (
            "declined_referral_rate",
            "declined referral rate",
            "fact_referrals",
            "f.declined_referrals",
            "f.referrals",
            True,
            ("specialty", "region"),
        ),
        (
            "referral_wait",
            "referral wait",
            "fact_referrals",
            "f.avg_wait_days*f.referrals",
            "f.referrals",
            True,
            ("specialty", "region"),
        ),
        (
            "closed_panels",
            "closed panels",
            "fact_network_capacity",
            "CASE WHEN f.panel_closed_flag THEN 1 ELSE 0 END",
            "1",
            False,
            ("specialty", "employer"),
        ),
        (
            "coordination_cost",
            "coordination cost",
            "fact_care_coordination",
            "f.coordination_cost_usd",
            "f.cases",
            True,
            ("region", "employer"),
        ),
    ]
    dimensions = {
        "specialty": (
            "JOIN dim_provider p ON p.provider_id=f.provider_id",
            "p.specialty",
        ),
        "employer": (
            "JOIN dim_employer_group e ON e.employer_id=f.employer_id",
            "e.name",
        ),
        "region": ("JOIN dim_region r ON r.region_id=f.region_id", "r.region_code"),
    }
    for metric, name, source, numerator, denominator, ratio, allowed in metrics:
        for dimension in allowed:
            join, group = dimensions[dimension]
            cases.append(
                ComparisonCase(
                    metric,
                    dimension,
                    name,
                    source,
                    numerator,
                    denominator,
                    join,
                    group,
                    ratio,
                )
            )
    return cases


def evaluate_comparison(result, case, tools):
    report = result.get("comparison", {})
    if result["status"] != "completed" or not report.get("verified"):
        return False
    request = report["request"]
    if request != {
        "metric_id": case.metric,
        "dimension": case.dimension,
        "baseline": {"start": "2026-01-01", "end": "2026-04-01"},
        "comparison": {"start": "2026-04-01", "end": "2026-07-01"},
        "filters": [],
    }:
        return False
    _, gold = tools.run_sql(case.gold_sql)
    totals = {}
    segments = {r["segment"]: r for r in report["segments"]}
    for quarter, period in ((1, "baseline"), (2, "comparison")):
        values = [r for r in gold if r[0] == quarter]
        num = sum(float(r[2]) for r in values)
        den = sum(float(r[3]) for r in values)
        totals[period] = num / den if case.ratio else num
        if not isclose(
            totals[period], report["summary"][period], rel_tol=1e-9, abs_tol=1e-7
        ):
            return False
        if {r[1] for r in values} != set(segments):
            return False
        for _, key, n, d in values:
            expected = float(n) / float(d) if case.ratio else float(n)
            if not isclose(expected, segments[key][period], rel_tol=1e-9, abs_tol=1e-7):
                return False
    change = totals["comparison"] - totals["baseline"]
    return isclose(
        change,
        sum(r["contribution"] for r in report["segments"]),
        rel_tol=1e-9,
        abs_tol=1e-7,
    )
