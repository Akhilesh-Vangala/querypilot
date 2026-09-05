from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from . import db as db_module
from .api import router
from .models import Base

logger = logging.getLogger("querypilot")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=db_module.engine)
    logger.info('{"event":"startup"}')
    yield


app = FastAPI(
    title="QueryPilot",
    version="1.0.0",
    description=(
        "Agentic natural-language-to-SQL analytics copilot over a healthcare claims "
        "star schema. Drafts read-only SQL, enforces statement guardrails, and scores "
        "answers with execution accuracy against a golden set."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3007",
        "http://127.0.0.1:3007",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
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
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    if isinstance(exc, PydanticValidationError):
        logger.exception('{"event":"response_model_error"}')
        return JSONResponse(status_code=500, content={"detail": "internal server error"})
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
        logger.warning('{"event":"ready","database_error":"%s"}', exc)
    return {"ready": all(checks.values()), "checks": checks}


app.include_router(router)
