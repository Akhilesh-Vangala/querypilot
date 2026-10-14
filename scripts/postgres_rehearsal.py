"""Execute real PostgreSQL authority, concurrency, lease, and warehouse checks."""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from app import db
from app.models import User, AnalysisRun
from app.runs import RunRepository, RunConflict
from app.worker import process_one
from app.production_checks import verify_warehouse_role
from app.agent.tools import WarehouseTools
from app.eval.golden import GOLDEN, results_match

verify_warehouse_role(db.warehouse_engine)
assert db.engine.dialect.name == "postgresql"
with Session(db.engine) as session:
    analyst = session.scalar(select(User).where(User.role == "analyst")).id
    admin = session.scalar(select(User).where(User.role == "admin")).id
# Rehearsal uses a new namespace, without deleting existing warehouse or user records.
namespace = "rehearsal-" + str(time.time_ns())
repo = RunRepository(db.engine)
runs = [
    repo.admit(analyst, case.question, namespace + "-" + case.id) for case in GOLDEN
]
assert (
    repo.admit(analyst, GOLDEN[0].question, namespace + "-" + GOLDEN[0].id)["id"]
    == runs[0]["id"]
)
with ThreadPoolExecutor(max_workers=4) as pool:

    def work(_):
        count = 0
        while process_one(RunRepository(db.engine)):
            count += 1
        return count

    workers = list(pool.map(work, range(4)))
assert sum(workers) == len(runs)
passed = 0
with Session(db.engine) as session:
    tools = WarehouseTools(session)
    for run, case in zip(runs, GOLDEN):
        result = repo.get(run["id"], analyst)["result"]
        assert result is not None, repo.get(run["id"], analyst)
        if case.must_refuse:
            assert result["refused"]
        else:
            _, expected = tools.run_sql(case.sql)
            assert results_match(expected, result["rows"]), case.id
        assert result["framework"] == "LangGraph"
        passed += 1
    try:
        tools.run_sql("SELECT missing_column FROM fact_claims")
    except Exception:
        pass
    assert session.scalar(select(User).limit(1))
for role_engine, sql in [
    (db.warehouse_engine, "SELECT email FROM users"),
    (db.warehouse_engine, "UPDATE fact_claims SET claim_count=0"),
    (db.engine, "SELECT * FROM fact_claims"),
]:
    try:
        with role_engine.begin() as connection:
            connection.execute(text(sql))
    except Exception:
        pass
    else:
        raise AssertionError("Database role allowed forbidden access")
try:
    repo.get(runs[0]["id"], admin)
except LookupError:
    pass
else:
    raise AssertionError("Cross-user history access allowed")
run = repo.admit(analyst, "Claims paid by specialty", namespace + "-lease")
job = repo.claim()
assert job["id"] == run["id"]
with db.engine.begin() as conn:
    conn.execute(
        text("UPDATE analysis_runs SET lease_until=:expired WHERE id=:id"),
        {"id": run["id"], "expired": time.time() - 1},
    )
assert repo.claim() is None
try:
    repo.finish(job, result={"status": "completed"})
except RunConflict:
    pass
else:
    raise AssertionError("Stale owner published")
assert repo.get(run["id"], analyst)["status"] == "interrupted"
report = {
    "database": "PostgreSQL",
    "baseline_cases": passed,
    "workers": 4,
    "worker_claims": workers,
    "database_role_denials": 3,
    "cross_user_denial": True,
    "idempotency": True,
    "lease_fencing": True,
    "model_mode": "deterministic baseline",
    "paid_model_calls": 0,
    "held_out_live_accuracy": None,
}
path = Path("artifacts/generated/postgres-rehearsal.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
