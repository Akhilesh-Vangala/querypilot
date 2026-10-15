"""Independent expectations for visitor-owned aggregation, not sample warehouse SQL."""
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.uploads.api import attach
from app.uploads.ingestion import Upload, parse
from app.uploads.service import run


class CustomerUploadTests(unittest.TestCase):
    def upload(self, operation="sum", csv=None):
        return Upload(csv=csv or "region,amount,status\nEast,0.10,done\nEast,0.20,done\nWest,9.90,pending\nWest,-1.25,done\n",
                      mapping={"group": "c0", "measure": "c1", "filter": "c2"},
                      options={"operation": operation, "filter_value": "done"})

    def test_grouped_sum_and_exact_filter_use_uploaded_numbers(self):
        result = run(self.upload())
        self.assertEqual([(r["segment"], r["value"], r["records"]) for r in result["results"]], [("East", "0.30", 2), ("West", "-1.25", 1)])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["summary"]["included_rows"], 3)

    def test_average_uses_true_group_denominator(self):
        self.assertEqual(run(self.upload("average"))["results"][0]["value"], "0.15")

    def test_count_does_not_require_a_numeric_measure(self):
        upload = Upload(csv="name\na\nb\nc\n", options={"operation": "count"})
        result = run(upload)
        self.assertEqual(result["results"], [{"segment": "All records", "value": "3", "records": 3}])

    def test_new_file_changes_results_and_does_not_use_shared_warehouse(self):
        upload = self.upload(csv="region,amount,status\nNorth,1234.567891,done\n")
        self.assertEqual(run(upload)["results"][0]["value"], "1234.567891")

    def test_invalid_values_missing_values_and_unsupported_operation_refuse(self):
        for amount in ("", "NaN", "1e20", "1.0000001", "100000001"):
            with self.assertRaises(ValueError):
                run(self.upload(csv=f"region,amount,status\nNorth,{amount},done\n"))
        with self.assertRaises(ValueError):
            run(self.upload("arbitrary_sql"))

    def test_no_matching_rows_withholds_result(self):
        with self.assertRaisesRegex(ValueError, "No records"):
            run(self.upload(csv="region,amount,status\nNorth,9.99,pending\n"))

    def test_group_cardinality_bound_and_csv_header_validation(self):
        with self.assertRaisesRegex(ValueError, "100 groups"):
            run(Upload(csv="region,amount\n"+"".join(f"r{i},1\n" for i in range(101)), mapping={"group": "c0", "measure": "c1"}))
        with self.assertRaises(ValueError):
            parse("region,REGION\nx,1\n")

    def test_api_never_retains_other_customer_results_and_limits_chunked_body(self):
        app = FastAPI()
        attach(app, "QueryPilot", Path(__file__).resolve().parents[3])
        with TestClient(app) as client:
            response = client.post("/api/uploads/analyze", json=self.upload().model_dump())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertNotIn("review", response.json())
            result = client.post("/api/uploads/analyze", json=self.upload(csv="region,amount,status\nOther,8.25,done\n").model_dump()).json()
            self.assertEqual([r["segment"] for r in result["results"]], ["Other"])
            self.assertEqual(client.post("/api/uploads/profile", content=iter([b"x"*600000, b"x"*600000]), headers={"content-type": "application/json"}).status_code, 413)
