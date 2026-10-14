from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import inspect, text
import sqlite3
import time
import json
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..config import get_settings
from ..telemetry import span
from .guardrails import MAX_ROWS, GuardrailError, validate_sql

from .catalog import WAREHOUSE_TABLES


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class WarehouseTools:
    def __init__(self, session: Session):
        self.session = session

    def _engine(self) -> Engine:
        from ..db import warehouse_engine

        return warehouse_engine or self.session.get_bind()

    def list_tables(self) -> list[dict[str, Any]]:
        rows = []
        for name in WAREHOUSE_TABLES:
            with self._engine().connect() as connection:
                if self._engine().dialect.name == "postgresql":
                    count = connection.execute(
                        text(
                            "SELECT COALESCE(MAX(GREATEST(c.reltuples,0)),0) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=:name"
                        ),
                        {"name": name},
                    ).scalar_one()
                    kind = "estimate"
                else:
                    count = connection.execute(
                        text(f"SELECT COUNT(*) FROM {name}")
                    ).scalar_one()
                    kind = "exact"
            rows.append({"name": name, "row_count": int(count), "row_count_kind": kind})
        return rows

    def describe_table(self, name: str) -> dict[str, Any]:
        if name not in WAREHOUSE_TABLES:
            raise GuardrailError(f"unknown warehouse table '{name}'")
        inspector = inspect(self._engine())
        columns = [
            {"name": col["name"], "type": str(col["type"])}
            for col in inspector.get_columns(name)
        ]
        return {"name": name, "columns": columns}

    def preview(self, name: str, limit: int = 5) -> dict[str, Any]:
        if name not in WAREHOUSE_TABLES:
            raise GuardrailError(f"unknown warehouse table '{name}'")
        cap = max(1, min(int(limit), 50))
        columns, data = self.run_sql(f"SELECT * FROM {name} LIMIT {cap}")
        return {"name": name, "columns": columns, "rows": data}

    def run_sql(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        with span(
            "warehouse.query", **{"warehouse.dialect": self._engine().dialect.name}
        ):
            return self._run_sql(sql)

    def _run_sql(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        settings = get_settings()
        bind = self._engine()
        dialect = "postgres" if bind.dialect.name == "postgresql" else "sqlite"
        rewritten = validate_sql(
            sql, max_rows=settings.max_result_rows, dialect=dialect
        )
        # Model SQL never shares the auth/logging transaction. Errors roll back here.
        with bind.connect() as connection:
            with connection.begin():
                raw = connection.connection.driver_connection
                if bind.dialect.name == "postgresql":
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                    connection.execute(
                        text("SELECT set_config('statement_timeout', :timeout, true)"),
                        {"timeout": str(settings.statement_timeout_ms)},
                    )
                    connection.execute(text("SET LOCAL search_path = public"))
                elif bind.dialect.name == "sqlite":
                    deadline = time.monotonic() + settings.statement_timeout_ms / 1000
                    allowed = {
                        sqlite3.SQLITE_SELECT,
                        sqlite3.SQLITE_READ,
                        sqlite3.SQLITE_FUNCTION,
                    }

                    def authorize(action, arg1, arg2, database, trigger):
                        if (
                            action == sqlite3.SQLITE_READ
                            and arg1 not in WAREHOUSE_TABLES
                        ):
                            return sqlite3.SQLITE_DENY
                        return (
                            sqlite3.SQLITE_OK
                            if action in allowed
                            else sqlite3.SQLITE_DENY
                        )

                    raw.set_authorizer(authorize)
                    raw.set_progress_handler(
                        lambda: int(time.monotonic() > deadline), 1000
                    )
                try:
                    result = connection.execute(text(rewritten))
                    columns = list(result.keys())
                    if len(columns) > 64:
                        raise GuardrailError("Result exceeds the column budget")
                    rows = []
                    total_bytes = 0
                    for raw_row in result:
                        row = [_jsonable(v) for v in raw_row]
                        total_bytes += len(json.dumps(row, default=str).encode())
                        if total_bytes > 250000:
                            raise GuardrailError(
                                "Result exceeds the byte budget; aggregate or narrow the query"
                            )
                        rows.append(row)
                        if len(rows) >= settings.max_result_rows:
                            break
                    self.last_query = {
                        "sql": rewritten,
                        "row_count": len(rows),
                        "row_limit": settings.max_result_rows,
                        "possibly_truncated": len(rows) >= settings.max_result_rows,
                    }
                    return columns, rows
                finally:
                    if bind.dialect.name == "sqlite":
                        raw.set_authorizer(None)
                        raw.set_progress_handler(None, 0)


def schema_catalog(session: Session) -> list[dict[str, Any]]:
    tools = WarehouseTools(session)
    tables = []
    for entry in tools.list_tables():
        described = tools.describe_table(entry["name"])
        tables.append(
            {
                "name": entry["name"],
                "row_count": entry["row_count"],
                "row_count_kind": entry["row_count_kind"],
                "columns": described["columns"],
            }
        )
    return tables
