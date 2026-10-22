"""Versioned, payload-free provenance shared by guided and private execution.

An execution ID is a correlation identifier, never an authorization credential.
The attestation authenticates a report; these hashes do not authenticate a source.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import re
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

_ACTIVE = ContextVar("querypilot_run_id", default=None)
_ID = re.compile(r"[a-zA-Z0-9_-]{1,128}\Z")


def identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("Invalid execution identifier")
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


@contextmanager
def run_scope(run_id=None):
    token = _ACTIVE.set(identifier(run_id or uuid.uuid4().hex))
    try:
        yield _ACTIVE.get()
    finally:
        _ACTIVE.reset(token)


def current_run_id():
    return _ACTIVE.get() or uuid.uuid4().hex


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["run-v1"] = "run-v1"
    run_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")
    budget_run_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")
    parent_run_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,128}$")
    task: Literal["analytics"]
    mode: Literal["reviewed-aggregate", "baseline", "scripted", "live"]
    owner_scope: Literal["request-local", "operator-workspace"]
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    producer_versions: dict[str, str] = Field(min_length=1, max_length=8)
    verification_scope: Literal["declared-contract", "execution-only", "semantic-reconciliation"]
    verification_passed: bool
    check_count: int = Field(ge=1)
    evidence_count: int = Field(ge=0)
    billing: Literal["not-used", "provider-reported", "unknown"]

    @model_validator(mode="after")
    def boundaries(self):
        live = self.mode == "live"
        if live == (self.billing == "not-used"):
            raise ValueError("Execution mode and billing provenance disagree")
        if self.owner_scope == "request-local" and self.mode != "reviewed-aggregate":
            raise ValueError("Public upload scope cannot claim private live investigation")
        return self


def record(*, task, mode, owner_scope, input_sha256, contract, result,
           verification_scope, verification_passed, check_count, evidence_count,
           producer_versions, billing="not-used", run_id=None, budget_run_id=None,
           parent_run_id=None):
    identity = identifier(run_id or current_run_id())
    return RunRecord(run_id=identity, budget_run_id=identifier(budget_run_id or identity),
                     parent_run_id=parent_run_id, task=task, mode=mode, owner_scope=owner_scope,
                     input_sha256=input_sha256, contract_sha256=fingerprint(contract),
                     result_sha256=fingerprint(result), producer_versions=producer_versions,
                     verification_scope=verification_scope, verification_passed=verification_passed,
                     check_count=check_count, evidence_count=evidence_count, billing=billing).model_dump()


def upload_record(upload, report):
    return record(task="analytics", mode="reviewed-aggregate", owner_scope="request-local",
                  input_sha256=fingerprint({"csv": upload.csv, "mapping": upload.mapping, "options": upload.options}),
                  contract=report["contract"], result={k: report[k] for k in ("results", "sql", "checks") if k in report},
                  verification_scope="declared-contract", verification_passed=all(report["checks"].values()),
                  check_count=len(report["checks"]), evidence_count=report["summary"]["source_rows"],
                  producer_versions={"contract": "querypilot-upload-v1", "producer": fingerprint({
                      "service": hashlib.sha256(Path(__file__).parents[1].joinpath("uploads/service.py").read_bytes()).hexdigest(),
                      "record": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})})
