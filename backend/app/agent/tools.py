from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..config import get_settings
from .guardrails import MAX_ROWS, GuardrailError, validate_sql

WAREHOUSE_TABLES = (
    "dim_sku",
    "dim_plant",
    "dim_dc",
    "dim_date",
    "fact_sales",
    "fact_production",
    "fact_inventory",
    "fact_freight",
)


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
        return self.session.get_bind()

    def list_tables(self) -> list[dict[str, Any]]:
        rows = []
        for name in WAREHOUSE_TABLES:
            count = self.session.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar_one()
            rows.append({"name": name, "row_count": int(count)})
        return rows

    def describe_table(self, name: str) -> dict[str, Any]:
        if name not in WAREHOUSE_TABLES:
            raise GuardrailError(f"unknown warehouse table '{name}'")
        inspector = inspect(self._engine())
        columns = [
            {"name": col["name"], "type": str(col["type"])} for col in inspector.get_columns(name)
        ]
        return {"name": name, "columns": columns}

    def preview(self, name: str, limit: int = 5) -> dict[str, Any]:
        if name not in WAREHOUSE_TABLES:
            raise GuardrailError(f"unknown warehouse table '{name}'")
        cap = max(1, min(int(limit), 50))
        result = self.session.execute(text(f"SELECT * FROM {name} LIMIT {cap}"))
        columns = list(result.keys())
        data = [[_jsonable(v) for v in row] for row in result.fetchall()]
        return {"name": name, "columns": columns, "rows": data}

    def run_sql(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        rewritten = validate_sql(sql)
        settings = get_settings()
        bind = self._engine()
        if bind.dialect.name == "postgresql":
            self.session.execute(text(f"SET LOCAL statement_timeout = '{settings.statement_timeout_ms}'"))
        result = self.session.execute(text(rewritten))
        columns = list(result.keys())
        fetched = result.fetchmany(MAX_ROWS)
        rows = [[_jsonable(v) for v in row] for row in fetched]
        return columns, rows


def schema_catalog(session: Session) -> list[dict[str, Any]]:
    tools = WarehouseTools(session)
    tables = []
    for entry in tools.list_tables():
        described = tools.describe_table(entry["name"])
        tables.append(
            {
                "name": entry["name"],
                "row_count": entry["row_count"],
                "columns": described["columns"],
            }
        )
    return tables
