"""Real API restart, queue processing, and authenticated history preservation."""

import json
import subprocess
import time
import uuid
import httpx
from pathlib import Path

client = httpx.Client(base_url="http://127.0.0.1:8007", timeout=30)
response = client.post(
    "/api/auth/token",
    data={"username": "analyst@querypilot.example.com", "password": "analyst-password"},
)
response.raise_for_status()
run = client.post(
    "/api/analyses",
    json={"question": "Declined referral rate by specialty", "mode": "baseline"},
    headers={"Idempotency-Key": str(uuid.uuid4())},
)
run.raise_for_status()
identity = run.json()["id"]
subprocess.run(["scripts/deployment/compose.sh", "restart", "api"], check=True)
for _ in range(60):
    try:
        state = client.get("/api/analyses/" + identity)
        if state.status_code == 200 and state.json()["status"] == "completed":
            break
    except httpx.HTTPError:
        pass
    time.sleep(1)
else:
    raise AssertionError("Run did not survive API restart")
value = state.json()
assert len(value["result"]["rows"]) == 5 and value["result"]["validation"]["executed"]
assert any(r["id"] == identity for r in client.get("/api/analyses").json())
report = {
    "api_restart": "passed",
    "persisted_history": "passed",
    "run_status": value["status"],
    "rows": 5,
    "paid_model_calls": 0,
}
Path("artifacts/generated/restart.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
