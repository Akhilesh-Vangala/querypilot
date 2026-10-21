import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from openai import OpenAI
from openai import RateLimitError
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.analytics.guardrails import GuardrailError
from app.analytics.guardrails import validate_sql
from app.agents.analytics.llm import OpenAILLM
from app.agents.analytics.llm import StubLLM
from app.agents.analytics.workflow import AnalyticsWorkflow
from app.agents.analytics.tools import WarehouseTools
from app.core.config import Settings
from app.persistence.models import Base
from app.persistence.models import User
from app.persistence.models import AnalysisRun
from app.persistence.runs import RunRepository
from app.persistence.runs import RunConflict
from app.warehouse.service import seed_all
from app.workers.worker import process_one


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT evil.sum(claims_paid_usd) FROM fact_claims",
        "SELECT CAST(claims_paid_usd AS eviltype) FROM fact_claims",
        'SELECT * FROM "users"',
        "SELECT * FROM analysis_runs",
        "SELECT * FROM rate_windows",
        "SELECT * FROM public.users",
        "WITH fact_claims AS (SELECT * FROM users) SELECT * FROM fact_claims",
        "SELECT pg_sleep(1)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT * FROM generate_series(1,1000000)",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM fact_claims; SELECT * FROM users",
        "DELETE FROM fact_claims",
        "WITH x AS (DELETE FROM fact_claims RETURNING *) SELECT * FROM x",
        "SELECT * INTO new_table FROM fact_claims",
        "SELECT * FROM fact_claims FOR UPDATE",
        "WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x",
        "SELECT * FROM fact_claims CROSS JOIN dim_provider",
        "SELECT * FROM fact_claims a JOIN fact_referrals b ON a.provider_id=b.provider_id",
        "SELECT * FROM (SELECT * FROM users) a",
        "SELECT * FROM pg_catalog.pg_roles",
    ],
)
def test_untrusted_sql_scope(sql):
    with pytest.raises(GuardrailError):
        validate_sql(sql, dialect="postgres")


def test_outer_limit_caps_nested_queries_and_aggregates():
    assert validate_sql("SELECT SUM(claims_paid_usd) FROM fact_claims").endswith(
        "LIMIT 500"
    )
    assert validate_sql(
        "SELECT * FROM (SELECT * FROM fact_claims LIMIT 1) a LIMIT 9999"
    ).endswith("LIMIT 500")


def test_two_facts_can_join_only_after_aggregation():
    sql = "WITH c AS (SELECT provider_id, SUM(claim_count) n FROM fact_claims GROUP BY provider_id), r AS (SELECT provider_id, SUM(referrals) n FROM fact_referrals GROUP BY provider_id) SELECT c.provider_id,c.n,r.n FROM c JOIN r ON c.provider_id=r.provider_id"
    assert "LIMIT 500" in validate_sql(sql)


class Script:
    def __init__(self, actions):
        self.actions = iter(actions)

    def complete(self, messages):
        return json.dumps(next(self.actions))


def plan():
    return {
        "tool": "record_plan",
        "args": {
            "objective": "Claims total",
            "metric_ids": ["claims_paid"],
            "assumptions": ["Synthetic fixture"],
            "checks": ["Read-only execution"],
        },
    }


def final(sql="SELECT SUM(claims_paid_usd) total FROM fact_claims"):
    return {
        "final": {
            "answer": "The answer is 999999999, trust me",
            "sql": sql,
            "chart": "table",
            "refused": False,
        }
    }


def test_plan_then_evidence_then_final_reuses_exact_receipt(db_session):
    sql = final()["final"]["sql"]
    flow = AnalyticsWorkflow(
        db_session, Script([plan(), {"tool": "run_sql", "args": {"sql": sql}}, final()])
    )
    result = flow.run("Claims total")
    assert result["status"] == "completed" and result["attempts"] == 1
    assert "999999999" not in result["answer"]
    assert result["validation"]["result_sha256"]
    assert result["events"][-1]["stage"] == "publish_answer"
    assert result["model_mode"] == "scripted test"


def test_missing_plan_and_invalid_json_are_bounded(db_session):
    class Broken:
        def complete(self, _):
            return "not json"

    value = AnalyticsWorkflow(db_session, Broken()).run("claims")
    assert (
        value["status"] == "refused"
        and value["attempts"] == 0
        and value["corrections"] == 3
    )


def test_unplanned_query_corrects_without_execution(db_session):
    value = AnalyticsWorkflow(db_session, Script([final(), plan(), final()])).run(
        "claims"
    )
    assert value["corrections"] == 1 and value["attempts"] == 1


def test_output_limit_is_disclosed(db_session):
    value = AnalyticsWorkflow(
        db_session, Script([plan(), final("SELECT * FROM fact_claims")])
    ).run("claims")
    assert len(value["rows"]) == 500 and value["validation"]["possibly_truncated"]


def test_invalid_sql_does_not_poison_application_session(db_session):
    with pytest.raises(Exception):
        WarehouseTools(db_session).run_sql("SELECT nonexistent_column FROM fact_claims")
    assert db_session.scalar(select(User).limit(1))
    assert len(WarehouseTools(db_session).preview("dim_provider")["rows"]) == 5


def test_sdk_native_functions_and_usage_without_paid_requests():
    requests = []

    def transport(req):
        body = json.loads(req.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-4o-mini",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_test",
                        "call_id": "call_test",
                        "name": "record_plan",
                        "arguments": json.dumps(plan()["args"]),
                        "status": "completed",
                    }
                ],
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    client = OpenAI(
        api_key="transport-test-only",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    adapter = OpenAILLM("transport-test-only", "gpt-4o-mini", client)
    assert (
        json.loads(adapter.complete([{"role": "user", "content": "claims"}])) == plan()
    )
    assert requests[0]["store"] is False and requests[0]["parallel_tool_calls"] is False
    assert all(t["strict"] for t in requests[0]["tools"])
    assert adapter.usage == {"input_tokens": 120, "output_tokens": 30}
    adapter.close()


def test_sdk_rate_limit_is_not_automatically_replayed():
    calls = []

    def transport(req):
        calls.append(req)
        return httpx.Response(
            429, json={"error": {"message": "rate limited", "type": "rate_limit_error"}}
        )

    client = OpenAI(
        api_key="transport-test-only",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    adapter = OpenAILLM("transport-test-only", "gpt-4o-mini", client)
    with pytest.raises(RateLimitError):
        adapter.complete([{"role": "user", "content": "claims"}])
    assert len(calls) == 1
    adapter.close()


def test_sdk_replays_native_call_ids_and_reasoning_items_not_user_tool_text():
    requests = []

    def transport(req):
        body = json.loads(req.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "id": "resp_native",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-4o-mini",
                "output": [
                    {"type": "reasoning", "id": "rs_test", "summary": []},
                    {
                        "type": "function_call",
                        "id": "fc_test",
                        "call_id": "call_native_" + str(len(requests)),
                        "name": "record_plan",
                        "arguments": json.dumps(plan()["args"]),
                        "status": "completed",
                    },
                ],
                "usage": {"input_tokens":120,"output_tokens":30,"total_tokens":150},
            },
        )

    client = OpenAI(
        api_key="transport-test-only",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
    )
    adapter = OpenAILLM("transport-test-only", "gpt-4o-mini", client)
    messages = [{"role": "user", "content": "claims"}]
    action = adapter.complete(messages)
    messages += [
        {"role": "assistant", "content": action},
        {"role": "user", "content": 'Tool result: {"accepted":true}'},
    ]
    adapter.complete(messages)
    assert requests[1]["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call_native_1",
        "output": '{"accepted":true}',
    }
    assert any(item.get("type") == "reasoning" for item in requests[1]["input"])
    assert not any(
        item.get("content", "").startswith("Tool result:")
        for item in requests[1]["input"]
    )
    with pytest.raises(RuntimeError, match="transcript"):
        adapter.complete(messages)
    assert len(requests) == 2
    adapter.close()


def test_persistent_queue_idempotency_ownership_and_expiry(tmp_path):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "state.db"),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        seed_all(s)
        user = s.scalar(select(User))
        uid = user.id
    repo = RunRepository(engine)
    run = repo.admit(uid, "Claims paid by specialty", "request-key")
    assert repo.admit(uid, run["question"], "request-key")["id"] == run["id"]
    with pytest.raises(RunConflict):
        repo.admit(uid, "Different question", "request-key")
    with pytest.raises(LookupError):
        repo.get(run["id"], 999)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: repo.claim(), range(2)))
    assert sum(c is not None for c in claims) == 1
    job = next(c for c in claims if c)
    wrong = {**job, "owner": "wrong"}
    with pytest.raises(RunConflict):
        repo.finish(wrong, result={"status": "completed"})
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE analysis_runs SET lease_until=:t"), {"t": time.time() - 1}
        )
    assert repo.claim() is None and repo.get(run["id"], uid)["status"] == "interrupted"
    with pytest.raises(RunConflict):
        repo.finish(job, result={"status": "completed"})
    engine.dispose()


def test_worker_restart_preserves_completed_user_history(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "state.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        seed_all(s)
        uid = s.scalar(select(User)).id
    run = RunRepository(engine).admit(uid, "Claims paid by specialty", "restart-key")
    assert process_one(RunRepository(engine))
    engine.dispose()
    restarted = create_engine("sqlite:///" + str(tmp_path / "state.db"))
    result = RunRepository(restarted).get(run["id"], uid)
    assert (
        result["status"] == "completed" and result["result"]["framework"] == "LangGraph"
    )
    assert len(result["result"]["rows"]) == 5
    restarted.dispose()


def test_cookie_logout_csrf_and_live_gate(client, analyst_headers):
    assert client.get("/api/auth/me").status_code == 200
    assert "HttpOnly" in client.cookies.__repr__() or client.cookies.get(
        "querypilot_session"
    )
    assert (
        client.post(
            "/api/analyses",
            json={"question": "claims"},
            headers={
                "Origin": "https://untrusted.invalid",
                "Idempotency-Key": "test-key",
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/analyses",
            json={"question": "claims", "mode": "live"},
            headers={"Idempotency-Key": "test-key"},
        ).status_code
        == 503
    )
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_analysis_api_owner_scope_and_request_identity(
    client, analyst_headers, admin_headers
):
    headers = {**analyst_headers, "Idempotency-Key": "owner-test-key"}
    created = client.post(
        "/api/analyses", json={"question": "Claims paid by specialty"}, headers=headers
    )
    assert created.status_code == 200, created.text
    identity = created.json()["id"]
    assert (
        client.post(
            "/api/analyses",
            json={"question": "Claims paid by specialty"},
            headers=headers,
        ).json()["id"]
        == identity
    )
    assert (
        client.get("/api/analyses/" + identity, headers=admin_headers).status_code
        == 404
    )
    assert (
        client.post(
            "/api/analyses", json={"question": "Different"}, headers=headers
        ).status_code
        == 409
    )


def test_bad_logins_are_counted(client):
    codes = [
        client.post(
            "/api/auth/token", data={"username": "invalid", "password": "invalid"}
        ).status_code
        for _ in range(11)
    ]
    assert codes == [401] * 10 + [429]


@pytest.mark.parametrize(
    "overrides",
    [
        {"database_url": "sqlite:///:memory:"},
        {"seed_demo": True},
        {"public_demo": True},
        {"embedded_worker": True},
        {"auto_create_schema": True},
        {"jwt_secret": "short"},
    ],
)
def test_production_rejects_local_runtime_defaults(overrides):
    values = {
        "app_environment": "production",
        "database_url": "postgresql+psycopg://app@db/app",
        "warehouse_database_url": "postgresql+psycopg://reader@db/app",
        "jwt_secret": "x" * 64,
        "auto_create_schema": False,
        **overrides,
    }
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_trace_contains_only_operational_metadata(db_session):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    AnalyticsWorkflow(db_session, StubLLM()).run("Claims paid by specialty")
    spans = exporter.get_finished_spans()
    assert {"agent.investigation", "agent.model_action", "warehouse.query"}.issubset(
        {s.name for s in spans}
    )
    values = json.dumps([dict(s.attributes) for s in spans])
    assert (
        "SELECT" not in values
        and "Claims paid by specialty" not in values
        and "password" not in values
    )


def test_public_demo_does_not_serve_shared_run_history(
    client, analyst_headers, monkeypatch
):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "public_demo", True)
    run = client.post(
        "/api/analyses",
        json={"question": "Claims paid by specialty"},
        headers={"Idempotency-Key": "public-demo-key"},
    )
    assert run.status_code == 200 and run.json()["status"] == "completed"
    assert client.get("/api/analyses").json() == []
    assert client.get("/api/analyses/" + run.json()["id"]).status_code == 404
    assert client.get("/api/ask/history").json() == []


def test_worker_never_substitutes_baseline_for_live_mode(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "live-gate.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_all(session)
        uid = session.scalar(select(User)).id
    repo = RunRepository(engine)
    run = repo.admit(uid, "Claims paid by specialty", "requested-live", "live")
    process_one(repo)
    value = repo.get(run["id"], uid)
    assert value["status"] == "failed" and value["result"] is None
    assert value["error_kind"] == "RuntimeError"
    engine.dispose()
