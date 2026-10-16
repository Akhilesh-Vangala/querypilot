"""Request-bounded own-data APIs and their standalone product workspace."""
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .ingestion import Upload, Preview, UploadBoundary, UploadProblem, fingerprint, profile, preview
from .service import run
from .signing import attest, verify_report

WRITE_PATHS = {"/api/uploads/profile", "/api/uploads/preview", "/api/uploads/analyze", "/api/uploads/analyze-stream", "/api/uploads/check-report", "/api/uploads/approve"}


class ReportCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    report: dict[str, Any] = Field(max_length=32)

CONFIGS = {
    "VerifyOps": {
        "title": "Find the discrepancy in your metric.",
        "description": "Upload a transaction export, declare its logical grain and eligibility rules, then reconcile exact totals and duplicate deliveries.",
        "fields": [["key", "Logical record key", True], ["amount", "Amount", True], ["group", "Group results by", False], ["status", "Eligibility status", False]],
        "options": [["unit", "Amount unit", ["dollars", "cents"]], ["eligible_status", "Include this status only", None], ["reported_total", "Reported total to compare (dollars)", None]],
        "template": "event_id,amount,category,status\nevent-101,125.50,Software,completed\nevent-101,125.50,Software,completed\nevent-102,74.50,Services,completed\nevent-103,90.00,Software,pending\n",
        "suggest": {"key": ["event_id", "id", "transaction_id"], "amount": ["amount", "revenue", "total"], "group": ["category", "region"], "status": ["status"]},
        "notice": "The key must identify a single logical record. Only exact duplicate rows can be collapsed; conflicting records stop the investigation. This workspace generates contract SQL, rather than executing an arbitrary SQL or dbt upload.",
    },
    "RelayOps": {
        "title": "Turn operational cases into reviewed updates.",
        "description": "Upload open short-shipment cases. Inspect evidence, policies and simulated outcomes before approving a downloadable change set.",
        "fields": [["order_id", "Order / case ID", True], ["ordered", "Ordered units", True], ["received", "Received units", True], ["invoiced", "Invoiced units", True], ["available", "Available replacement units", True], ["unit_price", "Unit price", True], ["confirmed", "Delivery confirmed (true / false)", True], ["pool", "Shared inventory pool / SKU", False]],
        "options": [["unit", "Price unit", ["dollars", "cents"]]],
        "template": "order_id,ordered_units,received_units,invoiced_units,available_units,unit_price,delivery_confirmed,inventory_pool\nPO-901,15,10,15,8,12.50,true,SKU-A\nPO-902,8,3,8,8,12.50,true,SKU-A\nPO-903,6,6,6,4,8.00,true,SKU-B\n",
        "suggest": {"order_id": ["order_id"], "ordered": ["ordered_units"], "received": ["received_units"], "invoiced": ["invoiced_units"], "available": ["available_units"], "unit_price": ["unit_price", "unit_cents"], "confirmed": ["delivery_confirmed"], "pool": ["inventory_pool", "sku"]},
        "notice": "Upload only open cases with no existing holds, claims or reservations. A mapped pool shares its initial stock across rows; without a pool, stock is allocated separately to each order. Approval exports proposed changes; it never writes to an ERP or supplier system.",
    },
    "QueryPilot": {
        "title": "Ask a precise question of your own data.",
        "description": "Map a measure, grouping and optional filter. Inspect the executed query and independently reconciled results from your CSV.",
        "fields": [["measure", "Numeric measure (optional for count)", False], ["group", "Group results by", False], ["filter", "Exact-match filter column", False]],
        "options": [["operation", "Metric operation", ["sum", "count", "average"]], ["filter_value", "Include this exact filter value", None]],
        "template": "transaction_id,region,amount,status\nT-001,East,125.50,completed\nT-002,West,74.50,completed\nT-003,East,40.00,pending\nT-004,West,25.50,completed\n",
        "suggest": {"measure": ["amount", "revenue", "cost", "value"], "group": ["region", "category"], "filter": []},
        "notice": "Select the business definition explicitly. Included numeric values must be present and valid; no imputation, duplicate removal or causal explanation is inferred. This workspace uses contract-driven SQL, without live language interpretation.",
    },
}


def attach(app, project, root):
    config = CONFIGS[project]
    static = Path(root)/"frontend/public/uploads"
    app.add_middleware(UploadBoundary)
    session = None
    if project == "RelayOps":
        from relayops.api.demo_security import DemoSession
        secret = os.getenv("RELAY_DEMO_SECRET", "")
        if not secret and os.getenv("RELAY_PUBLIC_SHOWCASE") != "1":
            secret = secrets.token_urlsafe(64)
        if secret:
            session = DemoSession(secret, "relay_upload_visitor")

    @app.get("/uploads", include_in_schema=False)
    def workspace():
        return FileResponse((Path(root)/"frontend/dist/index.html" if (Path(root)/"frontend/dist/index.html").exists() else Path(root)/"frontend/index.html"), headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})

    @app.get("/uploads/recording.html", include_in_schema=False)
    def recording():
        return FileResponse(static/"recording.html", headers={"Cache-Control": "no-store"})

    @app.get("/uploads/{name}", include_in_schema=False)
    @app.get("/uploads-assets/{name}", include_in_schema=False)
    def assets(name: str):
        if name not in ("index.html", "app.js", "style.css", "recording.html", "walkthrough.webm", "poster.png"):
            raise HTTPException(404, "Asset unavailable")
        if name == "index.html":
            return workspace()
        return FileResponse(static/name, headers={"Cache-Control": "no-store"})

    @app.get("/api/uploads/capabilities")
    def capabilities(request: Request, response: Response):
        if session:
            session.visitor(request, response)
        response.headers["Cache-Control"] = "no-store"
        return {"project": project, **{k: v for k, v in config.items() if k != "template"},
                "live_ai": False, "max_csv_bytes": 400000, "max_rows": 30 if project == "RelayOps" else 5000,
                "retention": "Unsaved files are processed for this request and remain in browser memory. Optional device history or configured account storage requires explicit save consent. Hosting metadata may be retained; file contents are not deliberately logged.",
                "approval_available": session is not None}

    @app.get("/api/uploads/template")
    def template():
        return Response(config["template"], media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{project.lower()}-template.csv"', "Cache-Control": "no-store"})

    @app.post("/api/uploads/profile")
    def inspect(upload: Upload):
        try:
            inspected = profile(upload.csv)
            if project == "RelayOps" and inspected["rows"] > 30:
                raise ValueError("Operational assessment supports at most 30 open cases per export")
            return inspected
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post("/api/uploads/analyze")
    def analyze(upload: Upload, request: Request):
        try:
            result = run(upload)
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        if session:
            result["review"] = session.seal({"visitor": session.visitor(request),
                "source": fingerprint({"csv": upload.csv, "mapping": upload.mapping, "options": upload.options}),
                "plan": result["plan_sha256"], "expires": int(time.time())+900}, "upload-review-v1")
        return JSONResponse(attest(result), headers={"Cache-Control": "no-store"})

    @app.post("/api/uploads/preview")
    def preview_rows(body: Preview):
        try:
            return preview(body)
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post("/api/uploads/analyze-stream")
    def analyze_stream(upload: Upload, request: Request):
        from .stream import stream
        def finish(result):
            if session:
                result["review"] = session.seal({"visitor": visitor,
                    "source": fingerprint({"csv": upload.csv, "mapping": upload.mapping, "options": upload.options}),
                    "plan": result["plan_sha256"], "expires": int(time.time())+900}, "upload-review-v1")
            return attest(result)
        visitor = session.visitor(request) if session else None
        return stream(upload, finish)

    @app.post("/api/uploads/check-report")
    def check_saved_report(body: ReportCheck):
        return {"verified": verify_report(body.report), "scope": "Authenticity of a past computed report; not a fresh source-system check."}

    @app.post("/api/uploads/approve")
    def approve_export(upload: Upload, request: Request):
        if project != "RelayOps":
            raise HTTPException(405, "This workspace is read-only")
        if not session:
            raise HTTPException(503, "Approval signing is not configured")
        state = session.open(upload.review, "upload-review-v1")
        if not hmac.compare_digest(state.get("visitor", ""), session.visitor(request)):
            raise HTTPException(403, "Review belongs to a different browser")
        source = fingerprint({"csv": upload.csv, "mapping": upload.mapping, "options": upload.options})
        if not hmac.compare_digest(state.get("source", ""), source):
            raise HTTPException(409, "File or contract changed after review; analyze again")
        try:
            preview = run(upload)
            if not hmac.compare_digest(state.get("plan", ""), preview["plan_sha256"]):
                raise HTTPException(409, "Plan changed after review; analyze again")
            result = run(upload, approved=True)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return JSONResponse(attest(result), headers={"Cache-Control": "no-store"})
