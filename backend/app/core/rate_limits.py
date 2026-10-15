"""Database-backed admission counters; no process-local production rate allowance."""

import hashlib
import time
from fastapi import HTTPException
from sqlalchemy import delete
from app.persistence.models import RateWindow


def consume(session, identity, limit, seconds=300):
    now = time.time()
    key = hashlib.sha256(f"{identity}:{int(now // seconds)}".encode()).hexdigest()
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(RateWindow).values(id=key, hits=1, expires_at=now + seconds * 2)
    statement = statement.on_conflict_do_update(
        index_elements=[RateWindow.id], set_={"hits": RateWindow.hits + 1}
    ).returning(RateWindow.hits)
    count = session.execute(statement).scalar_one()
    session.execute(delete(RateWindow).where(RateWindow.expires_at < now))
    if count > limit:
        session.commit()
        raise HTTPException(
            429,
            "Request allowance reached; try again later",
            headers={"Retry-After": str(seconds)},
        )
