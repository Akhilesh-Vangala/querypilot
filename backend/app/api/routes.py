from __future__ import annotations

from typing import Annotated
import re

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.analytics.planner import Planner
from app.agents.analytics.llm import StubLLM
from app.agents.analytics.tools import schema_catalog
from app.security.auth import create_access_token
from app.security.auth import get_current_user
from app.security.auth import require_role
from app.security.auth import verify_password
from app.persistence.db import get_db
from app.evaluation.golden import run_golden
from app.persistence.models import AskLog
from app.persistence.models import User
from app.api.schemas import AskRequest
from app.api.schemas import AnalysisRequest
from app.api.schemas import AskResponse
from app.api.schemas import EvalCaseResult
from app.api.schemas import EvalReportOut
from app.api.schemas import HistoryItem
from app.api.schemas import SchemaOut
from app.api.schemas import TokenOut
from app.api.schemas import UserOut

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_current_user)]


@router.post("/api/auth/token", response_model=TokenOut, tags=["auth"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
    response: Response,
    request: Request,
) -> TokenOut:
    from app.core.rate_limits import consume
    from app.core.config import get_settings

    consume(db, "login:" + request.client.host, 10)
    db.commit()
    user = db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.email, user.role)
    response.set_cookie(
        "querypilot_session",
        token,
        httponly=True,
        secure=get_settings().app_environment == "production"
        or request.url.scheme == "https",
        samesite="lax",
        max_age=get_settings().access_token_minutes * 60,
    )
    db.commit()
    return TokenOut(access_token=token)


@router.get("/api/auth/me", response_model=UserOut, tags=["auth"])
def me(user: UserDep) -> UserOut:
    return UserOut(email=user.email, full_name=user.full_name, role=user.role)


@router.get("/api/schema", response_model=SchemaOut, tags=["warehouse"])
def warehouse_schema(db: DbDep, _user: UserDep) -> SchemaOut:
    return SchemaOut(tables=schema_catalog(db))


@router.post("/api/ask", response_model=AskResponse, tags=["agent"])
def ask(payload: AskRequest, db: DbDep, user: UserDep) -> AskResponse:
    # Legacy endpoint remains an explicitly deterministic compatibility baseline.
    result = Planner(db, llm=StubLLM()).run(payload.question)
    db.add(
        AskLog(
            user_id=user.id,
            question=payload.question,
            sql=result.sql,
            answer=result.answer,
            refused=result.refused,
        )
    )
    db.commit()
    return AskResponse(
        answer=result.answer,
        sql=result.sql,
        chart=result.chart,
        rows=result.rows,
        columns=result.columns,
        attempts=result.attempts,
        refused=result.refused,
    )


@router.get("/api/ask/history", response_model=list[HistoryItem], tags=["agent"])
def ask_history(db: DbDep, user: UserDep) -> list[HistoryItem]:
    from app.core.config import get_settings

    if get_settings().public_demo:
        return []
    rows = db.scalars(
        select(AskLog)
        .where(AskLog.user_id == user.id)
        .order_by(AskLog.created_at.desc(), AskLog.id.desc())
        .limit(20)
    ).all()
    return [
        HistoryItem(
            id=row.id,
            question=row.question,
            sql=row.sql,
            answer=row.answer,
            refused=row.refused,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/api/eval/run", response_model=EvalReportOut, tags=["eval"])
def eval_run(
    db: DbDep, _admin: Annotated[User, Depends(require_role("admin"))]
) -> EvalReportOut:
    report = run_golden(db, llm=StubLLM())
    return EvalReportOut(
        score=report.score,
        n=report.n,
        passed=report.passed,
        results=[
            EvalCaseResult(
                id=row.id,
                question=row.question,
                passed=row.passed,
                refused=row.refused,
                predicted_sql=row.predicted_sql,
                detail=row.detail,
            )
            for row in report.results
        ],
    )


@router.get("/api/config", tags=["meta"])
def configuration():
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "data": "synthetic",
        "model_mode": "live"
        if settings.allow_live_ai and settings.openai_api_key
        else "deterministic baseline",
        "framework": "LangGraph",
        "contract_version": "claims-network-v2 + metric-comparison-v1",
        "capabilities": ["exploratory_sql", "compiled_metric_comparisons", "descriptive_shapley_attribution", "evidence_export"],
        "public_demo": settings.public_demo,
        "production_runtime": settings.app_environment == "production",
        "max_rows": settings.max_result_rows,
        "max_rounds": settings.max_model_rounds,
        "max_sql_attempts": settings.max_sql_attempts,
        "demo_accounts": settings.demo_accounts
        or settings.seed_demo
        or settings.public_demo,
        "history_scope": "this browser in public demo"
        if settings.public_demo
        else "authenticated user in PostgreSQL",
        "live_available": settings.allow_live_ai
        and bool(settings.openai_api_key)
        and not settings.public_demo,
    }


@router.get("/api/metrics", tags=["warehouse"])
def metrics(_user: UserDep):
    from app.analytics.catalog import CONTRACT
    from app.analytics.semantic import metric_catalog

    return {"metrics": metric_catalog(), "contract": CONTRACT}


@router.post("/api/analyses", tags=["agent"])
def create_analysis(
    payload: AnalysisRequest, db: DbDep, user: UserDep, request: Request
):
    from app.persistence.runs import RunRepository
    from app.persistence.runs import RunConflict
    from app.core.config import get_settings

    settings = get_settings()
    if payload.mode == "live" and (
        not settings.allow_live_ai
        or not settings.openai_api_key
        or settings.public_demo
    ):
        raise HTTPException(503, "Live AI is not privately configured")
    key = request.headers.get("idempotency-key", "")
    if not 8 <= len(key) <= 128 or not re.fullmatch(r"[A-Za-z0-9._:-]+", key):
        raise HTTPException(400, "Provide a bounded Idempotency-Key")
    from app.core.rate_limits import consume

    consume(db, "analysis:" + str(user.id), 30)
    db.commit()
    repository = RunRepository(db.get_bind())
    try:
        value = repository.admit(user.id, payload.question, key, payload.mode)
    except RunConflict as error:
        raise HTTPException(409, str(error)) from None
    if settings.public_demo and value["status"] == "queued":
        from app.workers.worker import process_one

        process_one(repository, identity=value["id"])
        value = repository.get(value["id"], user.id)
    return value


@router.get("/api/analyses", tags=["agent"])
def list_analyses(db: DbDep, user: UserDep):
    from app.core.config import get_settings

    if get_settings().public_demo:
        return []
    from app.persistence.runs import RunRepository

    return RunRepository(db.get_bind()).list(user.id)


@router.get("/api/analyses/{identity}", tags=["agent"])
def analysis_detail(identity: str, db: DbDep, user: UserDep):
    from app.core.config import get_settings

    if get_settings().public_demo:
        raise HTTPException(
            404,
            "Public demo investigations are retained only in the requesting browser",
        )
    from app.persistence.runs import RunRepository

    if not re.fullmatch(r"[a-f0-9]{32}", identity):
        raise HTTPException(404, "Investigation not found")
    try:
        return RunRepository(db.get_bind()).get(identity, user.id)
    except LookupError as error:
        raise HTTPException(404, str(error)) from None


@router.post("/api/auth/logout", tags=["auth"])
def logout(response: Response):
    response.delete_cookie("querypilot_session", httponly=True, samesite="lax")
    return {"signed_out": True}
