"""Product error recovery, signed evidence, streaming and hosted-account boundaries."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.product.accounts import Provider, attach as accounts
from app.uploads.api import attach as uploads
from app.uploads.ingestion import Preview, Upload, UploadProblem, preview, profile
from app.uploads.service import run
from app.uploads.signing import attest, verify_report

ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'region,amount,status\nNorth,0.10,done\nNorth,0.20,done\nSouth,5.00,pending\n'

def upload(source=SOURCE):
    return Upload(csv=source, mapping={'measure': 'c1', 'group': 'c0', 'filter': 'c2'}, options={'operation': 'sum', 'filter_value': 'done'})

class HostedAccountTests(unittest.TestCase):
    def setUp(self):
        self.owner = str(uuid4())
        self.calls, self.rows = [], []
        self.status = 200
        self.service = Provider("https://account.example", "sb_publishable_" + "x"*32, httpx.MockTransport(self.respond))
        app = FastAPI()
        uploads(app, "QueryPilot", ROOT)
        accounts(app, self.service)
        self.client = TestClient(app, base_url="https://verify.example")

    def respond(self, request):
        self.calls.append(request)
        if self.status != 200:
            return httpx.Response(self.status, text="private-provider-diagnostics-and-token")
        path = request.url.path
        if path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "access-private", "refresh_token": "refresh-private", "expires_in": 3600})
        if path.endswith("/user"):
            self.assertEqual(request.headers.get("authorization"), "Bearer access-private")
            return httpx.Response(200, json={"id": self.owner, "email": "person@example.com"})
        if path.startswith("/rest/"):
            self.assertEqual(request.headers["authorization"], "Bearer access-private")
            if request.method == "POST":
                self.rows.append(json.loads(request.content))
                return httpx.Response(201, json=[self.rows[-1]])
            if request.method == "GET":
                self.assertEqual(request.url.params.get("owner_id"), "eq." + self.owner)
                found = [r for r in self.rows if request.url.params.get("id", "eq."+r["id"]) == "eq."+r["id"]]
                return httpx.Response(200, json=found)
        return httpx.Response(204)

    def sign_in(self):
        return self.client.post("/api/account/sign-in", json={"email": "person@example.com", "password": "a-private-password"})

    def test_session_is_verified_and_tokens_are_only_secure_httponly_cookies(self):
        result = self.sign_in()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["id"], self.owner)
        self.assertNotIn("private", result.text)
        cookies = result.headers.get_list("set-cookie")
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("HttpOnly" in c and "Secure" in c and "SameSite=strict" in c and "__Host-" in c for c in cookies))
        self.assertEqual(self.client.get("/api/account/me").json()["id"], self.owner)
        self.assertEqual(self.client.post("/api/account/refresh", json={}).status_code, 200)

    def test_unauthenticated_history_is_not_shared_or_anonymous(self):
        self.assertEqual(self.client.get("/api/account/investigations").status_code, 401)
        self.assertEqual(self.rows, [])

    def test_server_recomputes_report_and_report_only_save_has_no_source_samples(self):
        self.sign_in()
        value = {"id": str(uuid4()), "title": "Revenue", "filename": "own.csv", "status": "completed", "upload": upload().model_dump(), "consent": True, "retain_source": False}
        self.assertEqual(self.client.post("/api/account/investigations", json=value).status_code, 200)
        row = self.rows[0]
        self.assertEqual(row["owner_id"], self.owner)
        self.assertIsNone(row["source"])
        self.assertEqual(row["profile"]["preview"], [])
        self.assertTrue(all("samples" not in c for c in row["profile"]["columns"]))
        self.assertTrue(verify_report(row["report"]))
        self.assertEqual(row["report"]["summary"]["overall_value"], "0.30")
        self.assertEqual(self.client.get("/api/account/investigations/"+row["id"]).json()["upload"]["csv"], "")
        value["id"] = str(uuid4())
        value["retain_source"] = True
        self.client.post("/api/account/investigations", json=value)
        self.assertEqual(self.rows[-1]["source"], SOURCE)

    def test_no_consent_or_spoofed_owner_or_client_report_can_be_saved(self):
        self.sign_in()
        value = {"id": str(uuid4()), "title": "Revenue", "filename": "own.csv", "status": "completed", "upload": upload().model_dump(), "consent": False}
        self.assertEqual(self.client.post("/api/account/investigations", json=value).status_code, 422)
        value.update(consent=True, owner_id=str(uuid4()), report={"passed": True})
        self.assertEqual(self.client.post("/api/account/investigations", json=value).status_code, 422)
        self.assertEqual(self.rows, [])

    def test_foreign_project_and_unowned_detail_are_unavailable(self):
        self.sign_in()
        self.assertEqual(self.client.get("/api/account/investigations/"+str(uuid4())).status_code, 404)
        value = {"id": str(uuid4()), "title": "Revenue", "filename": "own.csv", "project_id": str(uuid4()), "status": "draft", "upload": upload().model_dump(), "consent": True}
        self.assertEqual(self.client.post("/api/account/investigations", json=value).status_code, 404)
        self.assertFalse(self.rows)

    def test_provider_failure_and_validation_do_not_echo_credentials(self):
        for status, expected in ((429, 429), (500, 503), (400, 400)):
            self.status = status
            response = self.sign_in()
            self.assertEqual(response.status_code, expected)
            self.assertNotIn("private", response.text)
        response = self.client.post("/api/account/sign-in", json={"email": "bad", "password": {"secret": "must-not-reflect"}})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("must-not-reflect", response.text)

    def test_logout_clears_cookies_even_when_provider_unavailable(self):
        self.sign_in()
        self.status = 500
        result = self.client.post("/api/account/sign-out", json={})
        self.assertEqual(result.json(), {"signed_out": True, "provider_revoked": False})
        self.assertTrue(all("Max-Age=0" in c for c in result.headers.get_list("set-cookie")))

    def test_admin_keys_and_non_origin_provider_urls_are_refused(self):
        with self.assertRaises(ValueError):
            Provider("https://account.example", "sb_secret_admin")
        with self.assertRaises(ValueError):
            Provider("https://account.example/redirect", "sb_publishable_"+"x"*32)
        with patch.dict(os.environ, {"QUERY_ACCOUNT_SIGNUP": "0"}):
            self.assertFalse(self.client.get("/api/account/config").json()["signup_enabled"])
            self.assertEqual(self.client.post("/api/account/sign-up", json={}).status_code, 403)

    def test_missing_configuration_is_explicitly_disabled(self):
        app = FastAPI()
        with patch.dict(os.environ, {"QUERY_SUPABASE_URL": "", "QUERY_SUPABASE_PUBLISHABLE_KEY": ""}):
            accounts(app)
        with TestClient(app) as client:
            self.assertFalse(client.get("/api/account/config").json()["enabled"])
            self.assertEqual(client.post("/api/account/sign-in", json={}).status_code, 503)
