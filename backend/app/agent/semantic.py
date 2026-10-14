"""Executable reviewed metric comparisons. No model-authored SQL enters this path."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, localcontext
from itertools import permutations
import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlglot import exp

from .catalog import METRICS
from .guardrails import GuardrailError, validate_sql

VERSION = "metric-comparison-v1"
Dimension = Literal["specialty", "employer", "region"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Window(StrictModel):
    start: str
    end: str

    @model_validator(mode="after")
    def calendar_bounds(self):
        start, end = date.fromisoformat(self.start), date.fromisoformat(self.end)
        if start.isoformat() != self.start or end.isoformat() != self.end:
            raise ValueError("Use canonical YYYY-MM-DD dates")
        if not 1 <= (end - start).days <= 366:
            raise ValueError("Each half-open period must span 1–366 days")
        return self


class MetricFilter(StrictModel):
    dimension: Dimension
    value: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def portable_literal(self):
        if any(ord(c) < 32 for c in self.value) or "\\" in self.value:
            raise ValueError("Control characters/backslashes are unsupported")
        return self


# Row-level expressions, compatible dimensions and ratio semantics are owned here.
SPECS = {
    "claims_paid": (
        "fact_claims",
        "f.claims_paid_usd",
        "f.claim_count",
        False,
        ("specialty", "employer"),
    ),
    "declined_referral_rate": (
        "fact_referrals",
        "f.declined_referrals",
        "f.referrals",
        True,
        ("specialty", "region"),
    ),
    "referral_wait": (
        "fact_referrals",
        "f.avg_wait_days * f.referrals",
        "f.referrals",
        True,
        ("specialty", "region"),
    ),
    "closed_panels": (
        "fact_network_capacity",
        "CASE WHEN f.panel_closed_flag THEN 1 ELSE 0 END",
        "1",
        False,
        ("specialty", "employer"),
    ),
    "coordination_cost": (
        "fact_care_coordination",
        "f.coordination_cost_usd",
        "f.cases",
        True,
        ("region", "employer"),
    ),
}
DIMENSIONS = {
    "specialty": ("p.specialty", "JOIN dim_provider p ON p.provider_id=f.provider_id"),
    "employer": ("e.name", "JOIN dim_employer_group e ON e.employer_id=f.employer_id"),
    "region": ("r.region_code", "JOIN dim_region r ON r.region_id=f.region_id"),
}
NULL_CHECKS = {
    "claims_paid": "f.claims_paid_usd IS NULL OR f.claim_count IS NULL OR f.claims_paid_usd < 0 OR f.claim_count < 0 OR (f.claim_count=0 AND f.claims_paid_usd<>0)",
    "declined_referral_rate": "f.declined_referrals IS NULL OR f.referrals IS NULL OR f.referrals<0 OR f.declined_referrals<0 OR f.declined_referrals>f.referrals",
    "referral_wait": "f.avg_wait_days IS NULL OR f.referrals IS NULL OR f.avg_wait_days<0 OR f.referrals<0",
    "closed_panels": "f.panel_closed_flag IS NULL",
    "coordination_cost": "f.coordination_cost_usd IS NULL OR f.cases IS NULL OR f.coordination_cost_usd<0 OR f.cases<0 OR (f.cases=0 AND f.coordination_cost_usd<>0)",
}


class ComparisonRequest(StrictModel):
    metric_id: Literal[
        "claims_paid",
        "declined_referral_rate",
        "referral_wait",
        "closed_panels",
        "coordination_cost",
    ]
    dimension: Dimension
    baseline: Window
    comparison: Window
    filters: list[MetricFilter] = Field(max_length=3)

    @model_validator(mode="after")
    def supported_scope(self):
        if self.baseline.end > self.comparison.start:
            raise ValueError("Baseline must precede comparison without overlap")
        supported = SPECS[self.metric_id][4]
        dimensions = [f.dimension for f in self.filters]
        if self.dimension not in supported or any(
            d not in supported for d in dimensions
        ):
            raise ValueError("Dimension is not connected to this metric's fact grain")
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("Use one exact-match filter per dimension")
        return self


def metric_catalog():
    return [
        {
            **m,
            "comparison_dimensions": list(SPECS[m["id"]][4]),
            "executable_version": VERSION,
        }
        for m in METRICS
    ]


def compile_comparison(request: ComparisonRequest, dialect: str) -> str:
    """One statement/snapshot, separate total and segment aggregation of one fact."""
    table, numerator, denominator, _, _ = SPECS[request.metric_id]
    dimensions = sorted({request.dimension, *(f.dimension for f in request.filters)})
    joins = " ".join(DIMENSIONS[d][1] for d in dimensions)
    segment = DIMENSIONS[request.dimension][0]
    literal = lambda value: exp.Literal.string(value).sql(dialect=dialect)
    windows = {}
    for name in ("baseline", "comparison"):
        window = getattr(request, name)
        windows[name] = (
            f"d.date >= {literal(window.start)} AND d.date < {literal(window.end)}"
        )
    filters = "".join(
        f" AND {DIMENSIONS[f.dimension][0]}={literal(f.value)}" for f in request.filters
    )
    sql = f"""WITH scoped AS (
        SELECT CASE WHEN {windows["baseline"]} THEN 'baseline' ELSE 'comparison' END AS period,
        {segment} AS segment, {numerator} AS numerator, {denominator} AS denominator,
        CASE WHEN {NULL_CHECKS[request.metric_id]} OR {segment} IS NULL THEN 1 ELSE 0 END AS invalid,
        d.date AS source_date
        FROM {table} f JOIN dim_date d ON d.date_id=f.date_id {joins}
        WHERE (({windows["baseline"]}) OR ({windows["comparison"]})){filters}
    ), aggregates AS (
        SELECT period, 'total' AS level, '' AS segment, SUM(numerator) AS numerator,
        SUM(denominator) AS denominator, COUNT(*) AS observations, SUM(invalid) AS invalid_rows,
        COUNT(DISTINCT source_date) AS observed_weeks, MIN(source_date) AS first_date, MAX(source_date) AS last_date
        FROM scoped GROUP BY period
        UNION ALL
        SELECT period, 'segment' AS level, segment, SUM(numerator) AS numerator,
        SUM(denominator) AS denominator, COUNT(*) AS observations, SUM(invalid) AS invalid_rows,
        COUNT(DISTINCT source_date) AS observed_weeks, MIN(source_date) AS first_date, MAX(source_date) AS last_date
        FROM scoped GROUP BY period, segment
    ) SELECT aggregates.*,
        CASE WHEN period='baseline' THEN (SELECT COUNT(*) FROM dim_date d WHERE {windows["baseline"]})
        ELSE (SELECT COUNT(*) FROM dim_date d WHERE {windows["comparison"]}) END AS calendar_weeks,
        (SELECT MIN(date) FROM dim_date) AS warehouse_start,
        (SELECT MAX(date) FROM dim_date) AS warehouse_latest
        FROM aggregates ORDER BY level, segment, period"""
    return validate_sql(sql, dialect=dialect)


def decimal(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise GuardrailError("Non-finite metric evidence")
    return result


def shapley_claims(before: dict, after: dict):
    """Three-factor Shapley accounting: volume × segment mix × unit cost.

    Undefined unit costs (new/zero-volume segments) are never silently imputed.
    """
    keys = sorted(set(before) | set(after))
    if any(
        k not in before or k not in after or before[k][1] <= 0 or after[k][1] <= 0
        for k in keys
    ):
        return {
            "available": False,
            "reason": "New, removed or zero-volume segments have undefined unit cost; no imputation.",
        }
    totals = [sum(v[1] for v in group.values()) for group in (before, after)]
    if not keys or min(totals) <= 0:
        return {
            "available": False,
            "reason": "Positive claim volume is required in both periods.",
        }
    mixes = [
        {k: group[k][1] / totals[i] for k in keys}
        for i, group in enumerate((before, after))
    ]
    rates = [{k: group[k][0] / group[k][1] for k in keys} for group in (before, after)]

    def value(state):
        return totals[state[0]] * sum(
            mixes[state[1]][k] * rates[state[2]][k] for k in keys
        )

    effects = [Decimal(0)] * 3
    for order in permutations(range(3)):
        state = [0, 0, 0]
        for factor in order:
            prior = value(state)
            state[factor] = 1
            effects[factor] += (value(state) - prior) / 6
    change = sum(v[0] for v in after.values()) - sum(v[0] for v in before.values())
    return {
        "available": True,
        "method": "Three-factor Shapley; interactions averaged over all six factor orders",
        "volume": float(effects[0]),
        "mix": float(effects[1]),
        "unit_cost": float(effects[2]),
        "residual": float(change - sum(effects)),
    }


def verify_comparison(request: ComparisonRequest, columns, rows, query):
    """Check data quality and reconcile separately aggregated totals and breakdowns.

    This verifies a supported contract, not the interpretation of arbitrary prose.
    """
    with localcontext() as context:
        context.prec = 40
        return _verify(request, columns, rows, query)


def _verify(request, columns, rows, query):
    evidence = [dict(zip(columns, row, strict=True)) for row in rows]
    totals, groups = {}, {"baseline": {}, "comparison": {}}
    checks = []

    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "complete_result",
        not query["possibly_truncated"],
        "Row-limit hits cannot produce a verified comparison",
    )
    for row in evidence:
        period = row["period"]
        if period not in groups or row["level"] not in ("total", "segment"):
            raise GuardrailError("Unexpected compiled evidence shape")
        destination = totals if row["level"] == "total" else groups[period]
        key = period if row["level"] == "total" else row["segment"]
        if key in destination:
            raise GuardrailError("Duplicate aggregate evidence")
        destination[key] = row
    for period in groups:
        total = totals.get(period)
        check(
            f"{period}_present",
            total is not None,
            "Both requested periods need observations after filters",
        )
        if total is None:
            continue
        check(
            f"{period}_quality",
            total["invalid_rows"] == 0,
            "Non-null, nonnegative metric inputs and coherent denominators",
        )
        window = getattr(request, period)
        start, end = date.fromisoformat(window.start), date.fromisoformat(window.end)
        source_start, source_end = (
            date.fromisoformat(str(total["warehouse_start"])),
            date.fromisoformat(str(total["warehouse_latest"])),
        )
        covered = source_start <= start + timedelta(
            days=6
        ) and source_end >= end - timedelta(days=7)
        first_snapshot = start + timedelta(
            days=(source_start.weekday() - start.weekday()) % 7
        )
        expected_snapshots = max(0, ((end - first_snapshot).days + 6) // 7)
        check(
            f"{period}_coverage",
            covered
            and total["observed_weeks"] == total["calendar_weeks"]
            and total["calendar_weeks"] == expected_snapshots
            and expected_snapshots > 0,
            "Requested calendar window is covered at weekly snapshot resolution; this does not prove every provider-week was ingested",
        )
        for field in ("numerator", "denominator", "observations"):
            aggregate = decimal(total[field] or 0)
            segments = sum(
                (decimal(r[field] or 0) for r in groups[period].values()), Decimal(0)
            )
            check(
                f"{period}_{field}_reconciliation",
                abs(aggregate - segments)
                <= max(Decimal("0.000001"), abs(aggregate) * Decimal("1e-10")),
                "Independent total aggregation equals the sum of segment aggregations",
            )
    ratio = SPECS[request.metric_id][3]
    values, components = {}, {}
    for period, total in totals.items():
        n, d = decimal(total["numerator"] or 0), decimal(total["denominator"] or 0)
        if ratio:
            check(
                f"{period}_denominator",
                d > 0,
                "A zero denominator is undefined, not a zero rate",
            )
        values[period] = n / d if ratio and d > 0 else None if ratio else n
        components[period] = {
            key: (decimal(row["numerator"] or 0), decimal(row["denominator"] or 0))
            for key, row in groups[period].items()
        }
    verified = all(c["passed"] for c in checks)
    report = {
        "version": VERSION,
        "request": request.model_dump(),
        "verified": verified,
        "checks": checks,
        "source": {
            "transaction": "One read-only statement for both periods, totals and segments",
            "resolution": "Weekly snapshots; half-open calendar windows",
            "warehouse_latest": evidence[0]["warehouse_latest"] if evidence else None,
        },
        "limitations": [
            "Descriptive accounting, not causal attribution or patient-level outcomes.",
            "Calendar coverage does not establish complete ingestion at every fact grain.",
            "Original monetary storage is floating point; decimal arithmetic cannot recover storage precision.",
            "Model-selected scope requires analyst review; compiled semantics do not prove natural-language intent.",
        ],
    }
    if not verified:
        return {**report, "summary": None, "segments": [], "attribution": None}
    baseline, comparison = values["baseline"], values["comparison"]
    delta = comparison - baseline
    segments = []
    for key in sorted(set(groups["baseline"]) | set(groups["comparison"])):
        values_by_period, contributions = {}, {}
        for period in groups:
            n, d = components[period].get(key, (Decimal(0), Decimal(0)))
            total_d = decimal(totals[period]["denominator"] or 0)
            values_by_period[period] = (
                float(n / d) if ratio and d else None if ratio else float(n)
            )
            contributions[period] = n / total_d if ratio else n
        contribution = contributions["comparison"] - contributions["baseline"]
        segments.append(
            {
                "segment": key,
                **values_by_period,
                "contribution": float(contribution),
                "share_of_change": float(contribution / delta) if delta else None,
            }
        )
    residual = float(delta) - sum(s["contribution"] for s in segments)
    check(
        "change_reconciliation",
        abs(residual) <= max(1e-6, abs(float(delta)) * 1e-10),
        "Segment contributions reconcile to the observed total change",
    )
    attribution = (
        shapley_claims(components["baseline"], components["comparison"])
        if request.metric_id == "claims_paid"
        else None
    )
    if attribution and attribution["available"]:
        check(
            "factor_reconciliation",
            abs(attribution["residual"]) <= max(1e-6, abs(float(delta)) * 1e-10),
            "Volume + mix + unit-cost Shapley effects reconcile to claims-paid change",
        )
    report["verified"] = all(c["passed"] for c in checks)
    if not report["verified"]:
        return {**report, "summary": None, "segments": [], "attribution": None}
    return {
        **report,
        "summary": {
            "baseline": float(baseline),
            "comparison": float(comparison),
            "change": float(delta),
            "relative_change": float(delta / baseline) if baseline else None,
            "residual": residual,
            "unit": next(m["unit"] for m in METRICS if m["id"] == request.metric_id),
        },
        "segments": sorted(
            segments, key=lambda s: abs(s["contribution"]), reverse=True
        ),
        "attribution": attribution,
    }


def quarter_window(quarter, year):
    start = date(int(year), 3 * (int(quarter) - 1) + 1, 1)
    end = date(
        start.year + (start.month == 10),
        start.month % 12 + 3 if start.month != 10 else 1,
        1,
    )
    return {"start": start.isoformat(), "end": end.isoformat()}


NAMES = {
    "claims paid": "claims_paid",
    "declined referral rate": "declined_referral_rate",
    "referral wait": "referral_wait",
    "closed panels": "closed_panels",
    "coordination cost": "coordination_cost",
}


def guided_comparison(question):
    """Deliberately exact templates: never silently discard arbitrary user qualifiers."""
    match = re.fullmatch(
        r"Compare (claims paid|declined referral rate|referral wait|closed panels|coordination cost) from (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}) versus (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}) by (specialty|employer|region)\.?",
        question.strip(),
        re.I,
    )
    if match:
        name, a, b, c, d, dimension = match.groups()
        return ComparisonRequest(
            metric_id=NAMES[name.lower()],
            dimension=dimension.lower(),
            baseline=Window(start=a, end=b),
            comparison=Window(start=c, end=d),
            filters=[],
        )
    match = re.fullmatch(
        r"What explains the change in claims paid between Q([1-4]) and Q([1-4]) (20\d{2})\?",
        question.strip(),
        re.I,
    )
    if match:
        a, b, year = match.groups()
        return ComparisonRequest(
            metric_id="claims_paid",
            dimension="specialty",
            baseline=Window(**quarter_window(a, year)),
            comparison=Window(**quarter_window(b, year)),
            filters=[],
        )
    return None


def receipt_digest(request, columns, rows):
    def canonical(value):
        # Browsers serialize 123.0 as 123. Normalize numbers before hashing.
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            number = decimal(value)
            return format(number.normalize(), "f") if number else "0"
        if isinstance(value, list):
            return [canonical(v) for v in value]
        if isinstance(value, dict):
            return {k: canonical(v) for k, v in value.items()}
        return value

    return hashlib.sha256(
        json.dumps(
            canonical(
                {
                    "version": VERSION,
                    "request": request.model_dump(),
                    "columns": columns,
                    "rows": rows,
                }
            ),
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
