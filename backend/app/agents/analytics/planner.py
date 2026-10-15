from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.analytics.guardrails import GuardrailError
from app.agents.analytics.llm import LLMClient
from app.agents.analytics.llm import get_llm
from app.agents.analytics.llm import parse_action
from app.agents.analytics.tools import WarehouseTools

SYSTEM_PROMPT = """You are QueryPilot, an analytics agent over a healthcare claims and provider-network warehouse.
Reply with a single JSON object and no markdown.
Either {"tool": "list_tables"|"describe_table"|"preview"|"run_sql", "args": {...}}
or {"final": {"answer": str, "sql": str, "chart": "bar"|"line"|"table", "refused": bool}}.
Only a single SELECT or WITH ... SELECT is allowed. Never emit DDL or DML.
If the user asks to modify or destroy data, return final.refused=true and empty sql.
Prefer joining fact tables to dimensions. Use dim_date.year/quarter/month rather than dialect-specific date functions.
Last 12 months means date_id > (SELECT MAX(date_id) FROM dim_date) - 52.
"""


@dataclass
class AgentResult:
    answer: str
    sql: str
    chart: str
    rows: list[list[Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    attempts: int = 0
    refused: bool = False


class Planner:
    def __init__(self, session: Session, llm: LLMClient | None = None) -> None:
        self.session = session
        self.llm = llm or get_llm()
        self.tools = WarehouseTools(session)

    def _schema_text(self) -> str:
        parts = []
        for table in self.tools.list_tables():
            described = self.tools.describe_table(table["name"])
            cols = ", ".join(f"{c['name']} {c['type']}" for c in described["columns"])
            parts.append(f"{table['name']} ({table['row_count']} rows): {cols}")
        return "\n".join(parts)

    def _dispatch(self, name: str, args: dict[str, Any]) -> Any:
        if name == "list_tables":
            return self.tools.list_tables()
        if name == "describe_table":
            return self.tools.describe_table(str(args.get("name", "")))
        if name == "preview":
            return self.tools.preview(
                str(args.get("name", "")), int(args.get("limit", 5))
            )
        if name == "run_sql":
            raise GuardrailError("run_sql must go through the guarded execute path")
        raise GuardrailError(f"unknown tool '{name}'")

    def _execute_sql(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        return self.tools.run_sql(sql)

    def _summarize(self, columns: list[str], rows: list[list[Any]], hint: str) -> str:
        if hint:
            if len(rows) == 1:
                paired = ", ".join(f"{c}={v}" for c, v in zip(columns, rows[0]))
                return f"{hint} {paired}".strip()
            return hint
        if not rows:
            return "Query returned no rows."
        if len(rows) == 1:
            return ", ".join(f"{c}={v}" for c, v in zip(columns, rows[0]))
        return f"Returned {len(rows)} rows."

    def run(self, question: str) -> AgentResult:
        settings = get_settings()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Schema:\n{self._schema_text()}\n\nQuestion: {question}",
            },
        ]
        attempts = 0
        last_sql = ""

        for _step in range(8):
            raw = self.llm.complete(messages)
            try:
                action = parse_action(raw)
            except (ValueError, TypeError) as exc:
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": f"SQL error: response was not valid JSON ({exc}). Return a JSON object.",
                    }
                )
                continue

            if "tool" in action:
                name = str(action.get("tool"))
                args = action.get("args") or {}
                if name == "run_sql":
                    sql = str(args.get("sql") or "")
                    last_sql = sql
                    try:
                        attempts += 1
                        columns, rows = self._execute_sql(sql)
                    except GuardrailError as exc:
                        return AgentResult(
                            answer=f"Refused: {exc}",
                            sql=sql,
                            chart="table",
                            attempts=attempts,
                            refused=True,
                        )
                    except SQLAlchemyError as exc:
                        if attempts >= settings.max_sql_attempts:
                            return AgentResult(
                                answer=f"SQL failed after {attempts} attempts: {exc}",
                                sql=sql,
                                chart="table",
                                attempts=attempts,
                                refused=False,
                            )
                        messages.append({"role": "assistant", "content": raw})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"SQL error: {exc}. Retry with corrected SQL.",
                            }
                        )
                        continue
                    messages.append({"role": "assistant", "content": raw})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Tool result: columns={columns} rows={rows[:20]}",
                        }
                    )
                    continue
                try:
                    result = self._dispatch(
                        name, args if isinstance(args, dict) else {}
                    )
                except GuardrailError as exc:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": f"SQL error: {exc}"})
                    continue
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": f"Tool result: {result}"})
                continue

            final = action.get("final") or {}
            sql = str(final.get("sql") or "")
            chart = str(final.get("chart") or "table")
            if chart not in {"bar", "line", "table"}:
                chart = "table"
            refused = bool(final.get("refused")) or not sql.strip()
            if refused:
                return AgentResult(
                    answer=str(final.get("answer") or "Refused."),
                    sql=sql,
                    chart="table",
                    attempts=attempts,
                    refused=True,
                )
            last_sql = sql
            try:
                attempts += 1
                columns, rows = self._execute_sql(sql)
            except GuardrailError as exc:
                return AgentResult(
                    answer=f"Refused: {exc}",
                    sql=sql,
                    chart="table",
                    attempts=attempts,
                    refused=True,
                )
            except SQLAlchemyError as exc:
                if attempts >= settings.max_sql_attempts:
                    return AgentResult(
                        answer=f"SQL failed after {attempts} attempts: {exc}",
                        sql=sql,
                        chart="table",
                        attempts=attempts,
                        refused=False,
                    )
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": f"SQL error: {exc}. Retry with corrected SQL.",
                    }
                )
                continue
            return AgentResult(
                answer=self._summarize(columns, rows, str(final.get("answer") or "")),
                sql=sql,
                chart=chart,
                rows=rows,
                columns=columns,
                attempts=attempts,
                refused=False,
            )

        return AgentResult(
            answer="Agent stopped without a final answer.",
            sql=last_sql,
            chart="table",
            attempts=attempts,
            refused=False,
        )
