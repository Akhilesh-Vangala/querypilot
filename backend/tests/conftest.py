from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "querypilot-test-secret-0000000000000000000000000000000000000"
os.environ.pop("OPENAI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as db_module
from app.db import get_db
from app.main import app
from app.models import Base
from app.warehouse import seed_all

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_test_engine, "connect")
def _fk(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


db_module.engine = _test_engine
db_module.SessionLocal = sessionmaker(bind=_test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=_test_engine)
    session = db_module.SessionLocal()
    seed_all(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _token(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def analyst_headers(client):
    token = _token(client, "analyst@querypilot.example.com", "analyst-password")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client):
    token = _token(client, "admin@querypilot.example.com", "admin-password")
    return {"Authorization": f"Bearer {token}"}
