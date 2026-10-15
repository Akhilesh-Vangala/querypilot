"""Persistent run coordination; ownership and user scope are server-controlled."""

import hashlib
import time
import uuid
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from app.persistence.models import AnalysisRun
from app.persistence.models import utcnow


class RunConflict(ValueError):
    pass


class RunRepository:
    def __init__(self, engine):
        self.engine = engine
        self.factory = sessionmaker(bind=engine, expire_on_commit=False)

    def admission_lock(self, session):
        if self.engine.dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(882391064)"))
        else:
            session.execute(text("BEGIN IMMEDIATE"))

    def admit(self, user_id, question, key, mode="baseline"):
        question_hash = hashlib.sha256((mode + ":" + question).encode()).hexdigest()
        with self.factory.begin() as session:
            self.admission_lock(session)
            prior = session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.user_id == user_id, AnalysisRun.request_key == key
                )
            )
            if prior:
                if prior.request_hash != question_hash:
                    raise RunConflict("Idempotency key belongs to a different question")
                return self.public(prior)
            active = session.scalar(
                select(func.count())
                .select_from(AnalysisRun)
                .where(AnalysisRun.status.in_(["queued", "running"]))
            )
            if active >= 16:
                raise RunConflict(
                    "Investigation capacity reached; wait for active runs"
                )
            row = AnalysisRun(
                id=uuid.uuid4().hex,
                user_id=user_id,
                question=question,
                mode=mode,
                request_key=key,
                request_hash=question_hash,
                status="queued",
                events=[],
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(row)
            session.flush()
            return self.public(row)

    def claim(self, lease_seconds=60, identity=None):
        with self.factory.begin() as session:
            if self.engine.dialect.name != "postgresql":
                session.execute(text("BEGIN IMMEDIATE"))
            now = time.time()
            session.execute(
                update(AnalysisRun)
                .where(AnalysisRun.status == "running", AnalysisRun.lease_until < now)
                .values(
                    status="interrupted",
                    owner=None,
                    lease_until=None,
                    error_kind="LeaseExpired",
                    updated_at=utcnow(),
                )
            )
            query = (
                select(AnalysisRun)
                .where(AnalysisRun.status == "queued")
                .order_by(AnalysisRun.created_at, AnalysisRun.id)
                .limit(1)
            )
            if identity:
                query = query.where(AnalysisRun.id == identity)
            if self.engine.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            row = session.scalar(query)
            if row is None:
                return None
            owner = uuid.uuid4().hex
            row.status = "running"
            row.owner = owner
            row.lease_until = now + lease_seconds
            row.updated_at = utcnow()
            return {
                "id": row.id,
                "owner": owner,
                "question": row.question,
                "mode": row.mode,
            }

    def heartbeat(self, job):
        with self.factory.begin() as session:
            value = session.execute(
                update(AnalysisRun)
                .where(
                    AnalysisRun.id == job["id"],
                    AnalysisRun.owner == job["owner"],
                    AnalysisRun.status == "running",
                    AnalysisRun.lease_until >= time.time(),
                )
                .values(lease_until=time.time() + 60)
            )
            if value.rowcount != 1:
                raise RunConflict("Run ownership expired")

    def owned(self, session, job):
        query = select(AnalysisRun).where(AnalysisRun.id == job["id"])
        if self.engine.dialect.name == "postgresql":
            query = query.with_for_update()
        row = session.scalar(query)
        if (
            not row
            or row.owner != job["owner"]
            or row.status != "running"
            or row.lease_until < time.time()
        ):
            raise RunConflict("Run ownership expired")
        return row

    def event(self, job, event):
        with self.factory.begin() as session:
            if self.engine.dialect.name != "postgresql":
                session.execute(text("BEGIN IMMEDIATE"))
            row = self.owned(session, job)
            row.events = (row.events + [event])[-40:]
            row.updated_at = utcnow()

    def finish(self, job, result=None, error=None):
        with self.factory.begin() as session:
            if self.engine.dialect.name != "postgresql":
                session.execute(text("BEGIN IMMEDIATE"))
            row = self.owned(session, job)
            row.status = (
                ("interrupted" if error == "WorkerShutdown" else "failed")
                if error
                else result.get("status", "completed")
            )
            row.result = result
            row.error_kind = error
            row.owner = None
            row.lease_until = None
            row.updated_at = utcnow()

    @staticmethod
    def public(row):
        return {
            "id": row.id,
            "question": row.question,
            "status": row.status,
            "mode": row.mode,
            "result": row.result,
            "events": row.events,
            "error_kind": row.error_kind,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

    def get(self, identity, user_id):
        with self.factory() as session:
            row = session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == identity, AnalysisRun.user_id == user_id
                )
            )
            if row is None:
                raise LookupError("Investigation not found")
            return self.public(row)

    def list(self, user_id):
        with self.factory() as session:
            rows = session.scalars(
                select(AnalysisRun)
                .where(AnalysisRun.user_id == user_id)
                .order_by(AnalysisRun.created_at.desc())
                .limit(50)
            )
            return [
                {
                    key: value
                    for key, value in self.public(row).items()
                    if key not in ("result", "events")
                }
                for row in rows
            ]
