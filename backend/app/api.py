from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .agent.planner import Planner
from .agent.tools import schema_catalog
from .auth import create_access_token, get_current_user, require_role, verify_password
from .db import get_db
from .eval.golden import run_golden
from .models import AskLog, User
from .schemas import (
    AskRequest,
    AskResponse,
    EvalCaseResult,
    EvalReportOut,
    HistoryItem,
    SchemaOut,
    TokenOut,
    UserOut,
)

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_current_user)]


@router.post("/api/auth/token", response_model=TokenOut, tags=["auth"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
) -> TokenOut:
    user = db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(user.email, user.role))


@router.get("/api/auth/me", response_model=UserOut, tags=["auth"])
def me(user: UserDep) -> UserOut:
    return UserOut(email=user.email, full_name=user.full_name, role=user.role)


@router.get("/api/schema", response_model=SchemaOut, tags=["warehouse"])
def warehouse_schema(db: DbDep, _user: UserDep) -> SchemaOut:
    return SchemaOut(tables=schema_catalog(db))


@router.post("/api/ask", response_model=AskResponse, tags=["agent"])
def ask(payload: AskRequest, db: DbDep, user: UserDep) -> AskResponse:
    result = Planner(db).run(payload.question)
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
def eval_run(db: DbDep, _admin: Annotated[User, Depends(require_role("admin"))]) -> EvalReportOut:
    report = run_golden(db)
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
