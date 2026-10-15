from __future__ import annotations

import logging
import time
import uuid
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from app.persistence import db as db_module
from app.api.routes import router
from app.persistence.models import Base
from app.core.config import get_settings

logger = logging.getLogger("querypilot")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=db_module.engine)
    if settings.seed_demo:
        from app.warehouse.service import seed_all
        from sqlalchemy.orm import Session

        with Session(db_module.engine) as session:
            seed_all(session)
    if settings.app_environment == "production":
        from app.core.production_checks import verify_warehouse_role

        verify_warehouse_role(db_module.warehouse_engine)
    stopped = threading.Event()
    thread = None
    if settings.embedded_worker:
        from app.workers.worker import process_one
        from app.persistence.runs import RunRepository

        def work():
            repository = RunRepository(db_module.engine)
            while not stopped.is_set():
                if not process_one(repository, stopped):
                    stopped.wait(0.5)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
    logger.info('{"event":"startup"}')
    try:
        yield
    finally:
        stopped.set()
        if thread:
            thread.join(timeout=35)


app = FastAPI(
    title="QueryPilot",
    version="2.0.0",
    description=(
        "Agentic natural-language-to-SQL analytics copilot over a healthcare claims "
        "star schema. Plans bounded investigations, enforces read-only SQL scope, and retains "
        "execution provenance. A deterministic comparator is evaluated separately."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        value.strip()
        for value in get_settings().allowed_origins.split(",")
        if value.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    settings = get_settings()
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        expected = request.url.scheme + "://" + request.headers.get("host", "")
        allowed = {value.strip() for value in settings.allowed_origins.split(",")}
        if origin and origin != expected and origin not in allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin changes are not allowed"},
            )
        if (
            request.headers.get("content-length", "").isdigit()
            and int(request.headers["content-length"]) > 20000
        ):
            return JSONResponse(
                status_code=413, content={"detail": "Request exceeds the body limit"}
            )
    request_id = str(uuid.uuid4())[:8]
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        '{"event":"request","id":"%s","method":"%s","path":"%s","status":%d,"ms":%.1f}',
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    if isinstance(exc, PydanticValidationError):
        logger.exception('{"event":"response_model_error"}')
        return JSONResponse(
            status_code=500, content={"detail": "internal server error"}
        )
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready() -> dict:
    checks = {"database": False}
    try:
        with db_module.engine.connect() as conn:
            conn.execute(text("select 1"))
        checks["database"] = True
    except Exception as exc:  # pragma: no cover - depends on deployment
        logger.warning(
            '{"event":"ready","database_error_kind":"%s"}', type(exc).__name__
        )
    value = {"ready": all(checks.values()), "checks": checks}
    return value if value["ready"] else JSONResponse(value, status_code=503)


app.include_router(router)
