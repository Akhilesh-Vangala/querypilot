"""Independent small data variants: weighted metrics, partitions and accounting."""

from datetime import date
from datetime import timedelta
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.comparison import ComparisonWorkflow
from app.analytics.guardrails import GuardrailError
from app.agents.analytics.llm import StubLLM
from app.agents.analytics.protocol import tool_definitions
from app.analytics.semantic import ComparisonRequest
from app.analytics.semantic import Window
from app.analytics.semantic import MetricFilter
from app.analytics.semantic import SPECS
from app.analytics.semantic import compile_comparison
from app.analytics.semantic import guided_comparison
from app.analytics.semantic import shapley_claims
from app.analytics.semantic import verify_comparison
from app.analytics.semantic import receipt_digest
from app.agents.analytics.tools import WarehouseTools
from app.agents.analytics.workflow import AnalyticsWorkflow
from app.persistence.models import Base
from app.persistence.models import DimProvider
from app.persistence.models import DimDate
from app.persistence.models import DimEmployerGroup
from app.persistence.models import DimRegion
from app.persistence.models import FactClaims
from app.persistence.models import FactReferrals
from app.persistence.models import FactNetworkCapacity
from app.persistence.models import FactCareCoordination


def request(metric="claims_paid", dimension="specialty", **overrides):
    return ComparisonRequest.model_validate(
        {
            "metric_id": metric,
            "dimension": dimension,
            "baseline": {"start": "2026-01-01", "end": "2026-04-01"},
            "comparison": {"start": "2026-04-01", "end": "2026-07-01"},
            "filters": [],
            **overrides,
        }
    )


@pytest.fixture()
def variant_factory():
    engines = []

    def make(seed):
        engine = create_engine("sqlite:///:memory:")
        engines.append(engine)
        Base.metadata.create_all(engine)
        raw = []
        with Session(engine) as s:
            s.add_all(
                [
                    DimProvider(
                        provider_id=i,
                        npi=str(i),
                        specialty="Cardiology" if i < 3 else "Oncology",
                        group_name="Fixture",
                    )
                    for i in range(1, 5)
                ]
            )
            s.add_all(
                [
                    DimEmployerGroup(
                        employer_id=i,
                        name="Acme" if i == 1 else "O'Brien",
                        employer_code=str(i),
                        industry="Fixture",
                    )
                    for i in (1, 2)
                ]
            )
            s.add_all(
                [
                    DimRegion(
                        region_id=i, region_code=str(i), name=str(i), country="US"
                    )
                    for i in (1, 2)
                ]
            )
            dates = [date(2026, 1, 7) + timedelta(weeks=i) for i in range(25)]
            for index, day in enumerate(dates, 1):
                s.add(
                    DimDate(
                        date_id=index,
                        date=day,
                        year=2026,
                        quarter=1 if day.month < 4 else 2,
                        month=day.month,
                        week=index,
                    )
                )
            s.flush()
            for week in range(1, len(dates) + 1):
                for provider in range(1, 5):
                    for group in (1, 2):
                        # Strongly uneven denominators defeat unweighted averages.
                        n = (provider**2 * group + seed * week) * (
                            1 if week <= 12 else provider + 1
                        )
                        spend = n * (10 + provider * 7 + seed * week)
                        declined = n // (provider + 1)
                        wait = provider * 2 + week + seed
                        closed = (week + provider + group + seed) % 3 == 0
                        s.add(
                            FactClaims(
                                date_id=week,
                                provider_id=provider,
                                employer_id=group,
                                claim_count=n,
                                claims_paid_usd=spend,
                            )
                        )
                        s.add(
                            FactReferrals(
                                date_id=week,
                                provider_id=provider,
                                region_id=group,
                                referrals=n,
                                declined_referrals=declined,
                                avg_wait_days=wait,
                            )
                        )
                        s.add(
                            FactNetworkCapacity(
                                date_id=week,
                                provider_id=provider,
                                employer_id=group,
                                open_panel_slots=0 if closed else 3,
                                panel_closed_flag=closed,
                            )
                        )
                        raw.append(
                            {
                                "period": "baseline" if week <= 12 else "comparison",
                                "specialty": "Cardiology"
                                if provider < 3
                                else "Oncology",
                                "employer": "Acme" if group == 1 else "O'Brien",
                                "region": str(group),
                                "claims_paid": (spend, n),
                                "declined_referral_rate": (declined, n),
                                "referral_wait": (wait * n, n),
                                "closed_panels": (int(closed), 1),
                            }
                        )
                for region in (1, 2):
                    for employer in (1, 2):
                        n = region * employer * (seed + week)
                        cost = n * (week + employer * 13)
                        s.add(
                            FactCareCoordination(
                                date_id=week,
                                region_id=region,
                                employer_id=employer,
                                cases=n,
                                coordination_cost_usd=cost,
                            )
                        )
                        raw.append(
                            {
                                "period": "baseline" if week <= 12 else "comparison",
                                "region": str(region),
                                "employer": "Acme" if employer == 1 else "O'Brien",
                                "coordination_cost": (cost, n),
                            }
                        )
            s.commit()
        return engine, raw

    yield make
    for engine in engines:
        engine.dispose()


def oracle(raw, req):
    totals, segments = {}, {}
    for period in ("baseline", "comparison"):
        rows = [
            r
            for r in raw
            if req.metric_id in r
            and r["period"] == period
            and all(r[f.dimension] == f.value for f in req.filters)
        ]

        def value(entries):
            num = sum(r[req.metric_id][0] for r in entries)
            den = sum(r[req.metric_id][1] for r in entries)
            return (
                num / den
                if req.metric_id
                in ("declined_referral_rate", "referral_wait", "coordination_cost")
                else num
            )

        totals[period] = value(rows)
        segments[period] = {
            key: value([r for r in rows if r[req.dimension] == key])
            for key in {r[req.dimension] for r in rows}
        }
    return totals, segments


@pytest.mark.parametrize("seed", [1, 7, 29])
@pytest.mark.parametrize(
    "metric,dimension", [(m, d) for m, spec in SPECS.items() for d in spec[4]]
)
def test_executable_metric_matches_independent_row_oracle(
    variant_factory, seed, metric, dimension
):
    engine, raw = variant_factory(seed)
    req = request(metric, dimension)
    with Session(engine) as session:
        result = ComparisonWorkflow(
            WarehouseTools(session), req, lambda *a, **kw: None
        ).run()
    report = result["comparison"]
    expected, segments = oracle(raw, req)
    assert report["verified"], report["checks"]
    for period in expected:
        assert report["summary"][period] == pytest.approx(expected[period])
        for row in report["segments"]:
            assert row[period] == pytest.approx(segments[period][row["segment"]])
    change = expected["comparison"] - expected["baseline"]
    assert report["summary"]["change"] == pytest.approx(change)
    assert sum(s["contribution"] for s in report["segments"]) == pytest.approx(
        change, abs=1e-9
    )
    assert result["validation"]["result_sha256"] == receipt_digest(
        req, result["evidence"]["columns"], result["evidence"]["rows"]
    )


@pytest.mark.parametrize("metric", list(SPECS))
def test_exact_filter_and_quote_literal_bind_to_metric(variant_factory, metric):
    engine, raw = variant_factory(7)
    dimension = SPECS[metric][4][-1]
    value = "O'Brien" if dimension == "employer" else "2"
    req = request(
        metric, SPECS[metric][4][0], filters=[{"dimension": dimension, "value": value}]
    )
    with Session(engine) as session:
        result = ComparisonWorkflow(
            WarehouseTools(session), req, lambda *a, **kw: None
        ).run()
    expected, _ = oracle(raw, req)
    assert result["comparison"]["verified"]
    assert result["comparison"]["summary"]["baseline"] == pytest.approx(
        expected["baseline"]
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"dimension": "region"},
        {"metric_id": "unknown"},
        {"sql": "DROP TABLE users"},
        {"baseline": {"start": "2026-04-01", "end": "2026-01-01"}},
        {"baseline": {"start": "2026-01-01", "end": "2026-05-01"}},
        {"baseline": {"start": "2026-02-30", "end": "2026-03-01"}},
        {
            "filters": [
                {"dimension": "employer", "value": "x"},
                {"dimension": "employer", "value": "y"},
            ]
        },
        {"filters": [{"dimension": "specialty", "value": "bad\\literal"}]},
    ],
)
def test_unsupported_or_ambiguous_contract_rejected(overrides):
    with pytest.raises(ValidationError):
        request(**overrides)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "future",
        "zero",
        "negative",
        "truncated",
        "tampered_total",
        "missing_week",
        "calendar_gap",
    ],
)
def test_unverifiable_comparison_withholds_conclusions(variant_factory, mutation):
    engine, _ = variant_factory(7)
    req = request("declined_referral_rate")
    with engine.begin() as connection:
        if mutation == "empty":
            connection.execute(text("DELETE FROM fact_referrals WHERE date_id <= 12"))
        elif mutation == "zero":
            connection.execute(
                text("UPDATE fact_referrals SET referrals=0, declined_referrals=0")
            )
        elif mutation == "negative":
            connection.execute(
                text("UPDATE fact_referrals SET declined_referrals=referrals+1")
            )
        elif mutation == "calendar_gap":
            for table in (
                "fact_claims",
                "fact_referrals",
                "fact_network_capacity",
                "fact_care_coordination",
            ):
                connection.execute(text(f"DELETE FROM {table} WHERE date_id=2"))
            connection.execute(text("DELETE FROM dim_date WHERE date_id=2"))
        elif mutation == "missing_week":
            connection.execute(text("DELETE FROM fact_referrals WHERE date_id=1"))
    if mutation == "future":
        req = request(
            "declined_referral_rate",
            comparison={"start": "2027-04-01", "end": "2027-07-01"},
        )
    with Session(engine) as session:
        tools = WarehouseTools(session)
        cols, rows = tools.run_sql(compile_comparison(req, "sqlite"))
        if mutation == "tampered_total":
            target = next(r for r in rows if r[cols.index("level")] == "total")
            target[cols.index("numerator")] += 999
        if mutation == "truncated":
            tools.last_query["possibly_truncated"] = True
        report = verify_comparison(req, cols, rows, tools.last_query)
    assert (
        not report["verified"] and report["summary"] is None and not report["segments"]
    )


@pytest.mark.parametrize("factor", ["volume", "mix", "unit_cost"])
def test_shapley_isolates_each_factor_and_accounts_for_interactions(factor):
    before = {"A": (Decimal(100), Decimal(10)), "B": (Decimal(400), Decimal(20))}
    after = {
        "volume": {"A": (Decimal(200), Decimal(20)), "B": (Decimal(800), Decimal(40))},
        "mix": {"A": (Decimal(200), Decimal(20)), "B": (Decimal(200), Decimal(10))},
        "unit_cost": {
            "A": (Decimal(200), Decimal(10)),
            "B": (Decimal(800), Decimal(20)),
        },
    }[factor]
    effects = shapley_claims(before, after)
    delta = sum(v[0] for v in after.values()) - sum(v[0] for v in before.values())
    assert effects["available"] and effects[factor] == pytest.approx(float(delta))
    assert abs(effects["residual"]) < 1e-10
    for other in {"volume", "mix", "unit_cost"} - {factor}:
        assert effects[other] == pytest.approx(0, abs=1e-10)


def test_shapley_does_not_impute_new_segment_unit_cost():
    assert not shapley_claims(
        {"A": (Decimal(100), Decimal(10))}, {"B": (Decimal(200), Decimal(10))}
    )["available"]


def test_guided_comparison_is_full_workflow_with_no_live_call(db_session):
    result = AnalyticsWorkflow(db_session, StubLLM()).run(
        "What explains the change in claims paid between Q1 and Q2 2026?"
    )
    assert (
        result["comparison"]["verified"]
        and result["attempts"] == 1
        and result["rounds"] == 1
    )
    assert result["model_mode"] == "deterministic baseline" and result["usage"] == {}
    assert {
        "compile_metric_contract",
        "execute_comparison",
        "reconcile_metric_evidence",
        "publish_comparison_report",
    }.issubset({e["stage"] for e in result["events"]})
    # Arbitrary qualifiers cannot be silently dropped by the legacy Q1 classifier.
    ambiguous = AnalyticsWorkflow(db_session, StubLLM()).run(
        "Compare claims in Q1 versus Q2 2026 for Oncology only"
    )
    assert ambiguous["status"] == "needs_clarification" and not ambiguous["sql"]


def test_strict_sdk_comparison_schema_requires_every_nested_field():
    definition = next(t for t in tool_definitions() if t["name"] == "compare_metric")
    schema = definition["parameters"]
    for obj in [schema, *schema["$defs"].values()]:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_receipt_survives_browser_integer_serialization_but_detects_changes():
    req = request()
    assert receipt_digest(req, ["value"], [[123.0, -0.0]]) == receipt_digest(
        req, ["value"], [[123, 0]]
    )
    assert receipt_digest(req, ["value"], [[123.0]]) != receipt_digest(
        req, ["value"], [[124]]
    )


def test_weighted_contributions_handle_simpsons_paradox(variant_factory):
    engine, _ = variant_factory(7)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE fact_referrals SET referrals=0, declined_referrals=0")
        )
        for week, provider, n, declined in (
            (1, 1, 100, 90),
            (1, 3, 10, 1),
            (13, 1, 1, 1),
            (13, 3, 100, 20),
        ):
            connection.execute(
                text(
                    "UPDATE fact_referrals SET referrals=:n, declined_referrals=:declined WHERE date_id=:week AND provider_id=:provider AND region_id=1"
                ),
                {"n": n, "declined": declined, "week": week, "provider": provider},
            )
    with Session(engine) as session:
        report = ComparisonWorkflow(
            WarehouseTools(session),
            request("declined_referral_rate"),
            lambda *a, **kw: None,
        ).run()["comparison"]
    assert report["verified"]
    assert all(row["comparison"] > row["baseline"] for row in report["segments"])
    assert report["summary"]["change"] < 0
    assert sum(row["contribution"] for row in report["segments"]) == pytest.approx(
        21 / 101 - 91 / 110
    )


def test_filter_injection_is_only_a_literal_and_cannot_expand_scope(variant_factory):
    engine, _ = variant_factory(7)
    req = request(filters=[{"dimension": "employer", "value": "x' OR 1=1 --"}])
    with Session(engine) as session:
        tools = WarehouseTools(session)
        result = ComparisonWorkflow(tools, req, lambda *a, **kw: None).run()
        assert result["status"] == "needs_clarification"
        assert not result["comparison"]["verified"] and result["evidence"]["rows"] == []
        assert tools.run_sql("SELECT COUNT(*) FROM fact_claims")[1] == [[200]]


def test_offline_report_recomputes_and_detects_altered_summary(db_session):
    import copy
    from app.analytics.evidence import verify_artifact

    result = AnalyticsWorkflow(db_session, StubLLM()).run(
        "What explains the change in claims paid between Q1 and Q2 2026?"
    )
    payload = {"format": "querypilot-report-v1", "run": {"result": result}}
    assert verify_artifact(payload)["comparison_verified"]
    altered = copy.deepcopy(payload)
    altered["run"]["result"]["comparison"]["summary"]["change"] += 100
    with pytest.raises(ValueError, match="recomputed"):
        verify_artifact(altered)
    altered = copy.deepcopy(payload)
    altered["run"]["result"]["evidence"]["rows"][0][3] += 100
    with pytest.raises(ValueError, match="fingerprint"):
        verify_artifact(altered)


def test_live_style_typed_action_uses_compiler_and_plan_metric_binding(db_session):
    class Script:
        def __init__(self, actions):
            self.actions = iter(actions)

        def complete(self, messages):
            return json.dumps(next(self.actions))

    action = {"tool": "compare_metric", "args": request().model_dump()}
    result = AnalyticsWorkflow(db_session, Script([action])).run("Compare claims")
    assert result["comparison"]["verified"] and result["model_mode"] == "scripted test"
    mismatch = {
        "tool": "record_plan",
        "args": {
            "objective": "Referrals",
            "metric_ids": ["referral_wait"],
            "assumptions": [],
            "checks": [],
        },
    }
    refusal = {
        "final": {
            "answer": "Clarify the metric",
            "sql": "",
            "chart": "table",
            "refused": False,
        }
    }
    corrected = AnalyticsWorkflow(db_session, Script([mismatch, action, refusal])).run(
        "Compare claims"
    )
    assert corrected["corrections"] == 1 and corrected["attempts"] == 0
