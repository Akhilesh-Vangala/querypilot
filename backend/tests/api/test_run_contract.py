"""Actual public API/SSE and private worker provenance, without provider requests."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.run_contract import RunRecord
from app.uploads.api import attach

ROOT = Path(__file__).resolve().parents[3]
UPLOAD = {'csv': 'id,amount\na,12.34\nb,12.34\n', 'mapping': {'measure': 'c1'}, 'options': {'operation': 'sum'}}


class RunContractTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        attach(app, "QueryPilot", ROOT)
        self.client = TestClient(app)

    def test_public_run_identity_contract_binding_and_tamper_rejection(self):
        first = self.client.post("/api/uploads/analyze", json=UPLOAD)
        report = first.json()
        run = RunRecord.model_validate(report["run_record"])
        self.assertEqual(first.headers["x-run-id"], run.run_id)
        self.assertEqual(run.owner_scope, "request-local")
        self.assertEqual(run.billing, "not-used")
        other = self.client.post("/api/uploads/analyze", json=UPLOAD).json()["run_record"]
        self.assertNotEqual(run.run_id, other["run_id"])
        self.assertEqual(run.input_sha256, other["input_sha256"])
        changed = copy.deepcopy(UPLOAD)
        changed["options"]["operation"] = "average"
        second = self.client.post("/api/uploads/analyze", json=changed).json()["run_record"]
        self.assertNotEqual(run.input_sha256, second["input_sha256"])
        self.assertNotEqual(run.contract_sha256, second["contract_sha256"])
        report["run_record"]["verification_passed"] = False
        self.assertFalse(self.client.post("/api/uploads/check-report", json={"report": report}).json()["verified"])

    def test_stream_stages_and_final_report_have_one_correlation_id(self):
        response = self.client.post("/api/uploads/analyze-stream", json=UPLOAD)
        events = []
        for block in response.text.strip().split("\n\n"):
            if block.startswith("event:"):
                lines = block.splitlines()
                events.append((lines[0][7:], json.loads(lines[1][6:])))
        run = events[-1][1]["run_record"]
        self.assertTrue(all(e[1]["run_id"] == run["run_id"] for e in events if e[0] == "stage"))

    def test_public_record_cannot_claim_live_provider_verification(self):
        value = self.client.post("/api/uploads/analyze", json=UPLOAD).json()["run_record"]
        for changes in ({"mode": "live"}, {"billing": "provider-reported"}, {"private_source": "secret"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                RunRecord.model_validate({**value, **changes})
