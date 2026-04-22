"""Wire-level progress, durable receipt integrity and independent numeric contracts."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.uploads.api import attach
from app.uploads.ingestion import Upload, Preview, preview
from app.uploads.signing import attest, verify_report
from app.uploads.service import run

class ProductEvidenceTests(unittest.TestCase):
    def upload(self):
        return Upload(csv="region,amount,status\nNorth,0.10,done\nNorth,0.20,done\nSouth,5.00,pending\n",mapping={"group":"c0","measure":"c1","filter":"c2"},options={"operation":"sum","filter_value":"done"})

    def client(self):
        app=FastAPI()
        with patch.dict(os.environ, {"RELAY_DEMO_SECRET":"test-fixture-"+"x"*64}):
            attach(app,"QueryPilot",Path(__file__).resolve().parents[3])
        client=TestClient(app,base_url="https://product.test")
        client.get("/api/uploads/capabilities")
        return client

    def test_stream_contains_observed_stages_and_one_signed_terminal_report(self):
        with self.client() as client:
            response=client.post("/api/uploads/analyze-stream",json=self.upload().model_dump())
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers["x-accel-buffering"],"no")
            events=[]
            for block in response.text.split("\n\n"):
                if block.startswith("event: "):
                    lines=block.splitlines();events.append((lines[0][7:],json.loads(lines[1][6:])))
            self.assertEqual([kind for kind,_ in events].count("result"),1)
            self.assertEqual(events[-1][0],"result")
            self.assertEqual([v["stage"] for kind,v in events if kind=="stage" and v["state"]=="complete"],['source', 'contract', 'sql', 'reference', 'reconcile', 'report'])
            result=events[-1][1];self.assertTrue(verify_report(result))
            self.assertTrue(all(result["checks"].values()))
            self.assertFalse(result["live_ai"])

    def test_invalid_cell_stream_publishes_problem_never_result(self):
        upload=self.upload();upload.csv=upload.csv.replace('0.10','malformed-private-value')
        with self.client() as client:
            response=client.post("/api/uploads/analyze-stream",json=upload.model_dump())
            self.assertIn("event: problem",response.text)
            self.assertNotIn("event: result",response.text)
            block=response.text.split("event: problem\ndata: ")[-1].strip()
            problem=json.loads(block);self.assertTrue(problem["issues"])
            self.assertIn("row",problem["issues"][0])
            self.assertNotIn('malformed-private-value',problem["issues"][0]["message"])

    def test_deep_report_tampering_or_signing_key_rotation_fails_authentication(self):
        result=attest(run(self.upload()));self.assertTrue(verify_report(result))
        changed=copy.deepcopy(result);changed["summary"]["source_rows"]=99999
        self.assertFalse(verify_report(changed))
        with patch.dict(os.environ,{"QUERY_REPORT_SIGNING_KEY":"rotated-"+"z"*64}):
            self.assertFalse(verify_report(result))
        result["attestation"]["version"]="v2";self.assertFalse(verify_report(result))

    def test_late_source_record_can_be_inspected_without_first_page_sampling(self):
        csv="id,value\n"+"".join(f"row-{i},{i}\n" for i in range(40))
        found=preview(Preview(csv=csv,rows=[41]))
        self.assertEqual(found["rows"][0]["cells"][0],"row-39")
        self.assertEqual(found["rows"][0]["row"],41)

    def test_overall_average_uses_all_records_not_mean_of_group_averages(self):
        upload=Upload(csv="group,value\nA,2\nA,2\nB,10\n",mapping={"group":"c0","measure":"c1"},options={"operation":"average"})
        report=run(upload)
        self.assertEqual(report["summary"]["overall_value"],"4.6666666666666666666666666666666666667")
        self.assertNotEqual(report["summary"]["overall_value"],"6")

    def test_recording_assets_resolve_from_built_serverless_package(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            assets=root/'frontend/dist/uploads';assets.mkdir(parents=True)
            (assets/'poster.png').write_bytes(b'owned-built-poster')
            app=FastAPI();attach(app,'QueryPilot',root)
            with TestClient(app) as client:
                response=client.get('/uploads-assets/poster.png')
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.content,b'owned-built-poster')
