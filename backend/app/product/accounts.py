"""Optional hosted identity and owner-isolated, immutable investigation snapshots.

Provider access tokens stay in HttpOnly cookies. Every request is authorized by
the provider and then made with that user's token; there is no admin DB key.
"""
import base64
import json
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from ..uploads.ingestion import Upload, UploadProblem, profile
from ..uploads.service import run
from ..uploads.signing import attest, verify_report

UNAVAILABLE = "Cloud accounts have not been connected on this deployment."


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Credentials(Strict):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Identity(Strict):
    id: str


class Project(Identity):
    name: str = Field(min_length=1, max_length=80)
    consent: bool


class Investigation(Identity):
    title: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=160)
    project_id: str | None = None
    parent_id: str | None = None
    status: str = Field(pattern="^(draft|completed)$")
    upload: Upload
    retain_source: bool = False
    consent: bool


def identifier(value):
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(422, "A valid record ID is required") from None


async def parse(request, schema):
    try:
        return schema.model_validate(await request.json())
    except (ValueError, ValidationError):
        # Never reflect a submitted password, source cell or provider token.
        raise HTTPException(422, "Required fields are missing or invalid") from None


class Provider:
    def __init__(self, url, key, transport=None):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("QUERY_SUPABASE_URL must be an HTTPS origin")
        valid_key = key.startswith("sb_publishable_") and len(key) > 20
        if not valid_key:
            try:
                body = key.split(".")[1]
                claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
                valid_key = claims.get("role") == "anon"
            except (ValueError, IndexError, TypeError):
                valid_key = False
        if not valid_key:
            raise ValueError("Only a publishable or legacy anon key is allowed; never a service/admin key")
        self.url, self.key, self.transport = url.rstrip("/"), key, transport

    async def call(self, method, path, *, token=None, body=None, params=None, prefer=None):
        headers = {"apikey": self.key}
        if token:
            headers["Authorization"] = "Bearer " + token
        if prefer:
            headers["Prefer"] = prefer
        try:
            async with httpx.AsyncClient(transport=self.transport, trust_env=False, follow_redirects=False,
                                         timeout=httpx.Timeout(12, connect=5)) as client:
                async with client.stream(method, self.url + path, headers=headers, json=body, params=params) as reply:
                    chunks, size = [], 0
                    async for chunk in reply.aiter_bytes():
                        size += len(chunk)
                        if size > 1_200_000:
                            raise HTTPException(503, "Account response exceeded its safety limit")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    if reply.status_code == 429:
                        raise HTTPException(429, "Account service is busy; wait and try again")
                    if reply.status_code in (401, 403):
                        raise HTTPException(401, "Sign in again to access this account")
                    if reply.status_code == 409:
                        raise HTTPException(409, "This record conflicts with an existing snapshot or project")
                    if not 200 <= reply.status_code < 300:
                        detail = "Email or password was not accepted" if path.startswith("/auth/") and reply.status_code < 500 else "Account storage could not complete this request; check its configuration or retry"
                        raise HTTPException(400 if path.startswith("/auth/") and reply.status_code < 500 else 503, detail)
                    return json.loads(content) if content else None
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, "Account service could not be reached; retry without losing your current work") from None

    async def user(self, token):
        if not token:
            raise HTTPException(401, "Sign in to access your cloud account")
        value = await self.call("GET", "/auth/v1/user", token=token)
        if not isinstance(value, dict) or not value.get("id"):
            raise HTTPException(503, "Account service returned an incomplete identity")
        return {"id": identifier(value.get("id")), "email": value.get("email", "")}


def configure():
    url, key = os.getenv("QUERY_SUPABASE_URL"), os.getenv("QUERY_SUPABASE_PUBLISHABLE_KEY")
    if not url and not key:
        return None
    if not url or not key:
        raise ValueError("Both Supabase URL and publishable key are required")
    return Provider(url, key)


def names(request):
    prefix = "__Host-" if request.url.scheme == "https" else ""
    return prefix + "querypilot-access", prefix + "querypilot-refresh"


def session_cookies(request, response, session):
    access, refresh = names(request)
    values = ((access, session.get("access_token"), min(max(int(session.get("expires_in", 3600)), 60), 86400)),
              (refresh, session.get("refresh_token"), 7 * 86400))
    for name, value, ttl in values:
        if not value or not isinstance(value, str):
            raise HTTPException(503, "Account service did not return a complete session")
        response.set_cookie(name, value, max_age=ttl, secure=request.url.scheme == "https", httponly=True, samesite="strict", path="/")


def attach(app, provider=None):
    provider = provider or configure()

    def ready():
        if not provider:
            raise HTTPException(503, UNAVAILABLE)
        return provider

    async def actor(request):
        service = ready()
        token = request.cookies.get(names(request)[0])
        return service, token, await service.user(token)

    @app.get("/api/account/config")
    def configuration():
        return {"enabled": provider is not None, "provider": "Supabase",
                "signup_enabled": provider is not None and os.getenv("QUERY_ACCOUNT_SIGNUP") == "1",
                "reason": None if provider else UNAVAILABLE}

    @app.post("/api/account/sign-in")
    async def sign_in(request: Request, response: Response):
        service = ready()
        value = await parse(request, Credentials)
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.email):
            raise HTTPException(422, "Enter a valid email address")
        session = await service.call("POST", "/auth/v1/token", params={"grant_type": "password"}, body=value.model_dump())
        user = await service.user(session.get("access_token"))
        session_cookies(request, response, session)
        return user

    @app.post("/api/account/sign-up")
    async def sign_up(request: Request, response: Response):
        service = ready()
        if os.getenv("QUERY_ACCOUNT_SIGNUP") != "1":
            raise HTTPException(403, "Account registration is not enabled; contact the workspace owner")
        value = await parse(request, Credentials)
        if len(value.password) < 12 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.email):
            raise HTTPException(422, "Use a valid email and a password of at least 12 characters")
        session = await service.call("POST", "/auth/v1/signup", body=value.model_dump())
        if session.get("access_token"):
            user = await service.user(session["access_token"])
            session_cookies(request, response, session)
            return user
        return {"confirmation_required": True}

    @app.get("/api/account/me")
    async def me(request: Request):
        return (await actor(request))[2]

    @app.post("/api/account/refresh")
    async def refresh(request: Request, response: Response):
        service = ready()
        token = request.cookies.get(names(request)[1])
        if not token:
            raise HTTPException(401, "Sign in again to continue")
        session = await service.call("POST", "/auth/v1/token", params={"grant_type": "refresh_token"}, body={"refresh_token": token})
        user = await service.user(session.get("access_token"))
        session_cookies(request, response, session)
        return user

    @app.post("/api/account/sign-out")
    async def sign_out(request: Request, response: Response):
        revoked = False
        if provider and request.cookies.get(names(request)[0]):
            try:
                await provider.call("POST", "/auth/v1/logout", token=request.cookies[names(request)[0]], params={"scope": "local"})
                revoked = True
            except HTTPException:
                pass
        for name in names(request):
            response.delete_cookie(name, path="/", secure=request.url.scheme == "https", httponly=True, samesite="strict")
        return {"signed_out": True, "provider_revoked": revoked}

    async def records(request, table, select="*", record_id=None, limit=100):
        service, token, user = await actor(request)
        filters = {"owner_id": "eq." + user["id"], "select": select, "limit": str(limit), "order": "created_at.desc"}
        if record_id is not None:
            filters["id"] = "eq." + identifier(record_id)
        values = await service.call("GET", "/rest/v1/" + table, token=token, params=filters)
        if record_id is not None and not values:
            raise HTTPException(404, "This record was not found in your account")
        return values

    @app.get("/api/account/projects")
    async def projects(request: Request):
        return await records(request, "querypilot_projects", "id,name,created_at", limit=20)

    @app.post("/api/account/projects")
    async def create_project(request: Request):
        service, token, user = await actor(request)
        value = await parse(request, Project)
        if not value.consent or not value.name.strip():
            raise HTTPException(422, "A project name and storage consent are required")
        row = {"id": identifier(value.id), "owner_id": user["id"], "name": value.name.strip()}
        result = await service.call("POST", "/rest/v1/querypilot_projects", token=token, body=row, prefer="return=representation")
        return result[0]

    @app.get("/api/account/investigations")
    async def investigations(request: Request):
        return await records(request, "querypilot_investigations", "id,title,filename,status,source_sha256,project_id,created_at")

    @app.get("/api/account/investigations/{record_id}")
    async def investigation(request: Request, record_id: str):
        row = (await records(request, "querypilot_investigations", record_id=record_id, limit=1))[0]
        return {**row, "upload": {"csv": row.get("source") or "", **row["contract"]},
                "report_authentic": verify_report(row["report"]) if row.get("report") else False}

    @app.post("/api/account/investigations")
    async def save_investigation(request: Request):
        service, token, user = await actor(request)
        value = await parse(request, Investigation)
        if not value.consent or not value.title.strip():
            raise HTTPException(422, "A title and explicit storage consent are required")
        record_id = identifier(value.id)
        project_id = identifier(value.project_id) if value.project_id else None
        parent_id = identifier(value.parent_id) if value.parent_id else None
        if project_id:
            await records(request, "querypilot_projects", record_id=project_id, limit=1)
        if parent_id:
            await records(request, "querypilot_investigations", "id", record_id=parent_id, limit=1)
        try:
            inspected = await run_in_threadpool(profile, value.upload.csv)
            computed = await run_in_threadpool(run, value.upload) if value.status == "completed" else None
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        # No raw preview cells or samples survive a report-only cloud save.
        inspected["preview"] = []
        inspected["columns"] = [{k: v for k, v in c.items() if k != "samples"} for c in inspected["columns"]]
        row = {"id": record_id, "owner_id": user["id"], "title": value.title.strip(), "filename": value.filename,
               "project_id": project_id, "parent_id": parent_id, "status": value.status,
               "source_sha256": inspected["sha256"], "profile": inspected,
               "contract": {"mapping": value.upload.mapping, "options": value.upload.options},
               "source": value.upload.csv if value.retain_source else None,
               "report": attest(computed) if computed else None}
        await service.call("POST", "/rest/v1/querypilot_investigations", token=token, body=row, prefer="return=minimal")
        return {"id": record_id, "saved": True}

    async def delete(request, table):
        service, token, user = await actor(request)
        record = await parse(request, Identity)
        await records(request, table, "id", record_id=record.id, limit=1)
        await service.call("DELETE", "/rest/v1/" + table, token=token,
                           params={"owner_id": "eq." + user["id"], "id": "eq." + identifier(record.id)})
        return {"deleted": True}

    @app.post("/api/account/projects/delete")
    async def delete_project(request: Request):
        return await delete(request, "querypilot_projects")

    @app.post("/api/account/investigations/delete")
    async def delete_investigation(request: Request):
        return await delete(request, "querypilot_investigations")
