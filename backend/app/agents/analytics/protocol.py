"""Strict public action schemas shared by the SDK adapter and owned workflow."""

from typing import Literal
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ModelPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objective: str = Field(min_length=1, max_length=1000)
    metric_ids: list[str] = Field(max_length=5)
    assumptions: list[str] = Field(max_length=5)
    checks: list[str] = Field(max_length=5)


class ModelFinal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str = Field(max_length=2000)
    sql: str = Field(max_length=24000)
    chart: Literal["bar", "line", "table"]
    refused: bool


def tool_definitions():
    def definition(name, description, properties, required):
        return {
            "type": "function",
            "name": name,
            "description": description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        }

    return [
        {
            "type": "function",
            "name": "compare_metric",
            "description": "Compare a reviewed metric across two explicit nonoverlapping half-open YYYY-MM-DD periods, by specialty, employer (name) or region (code) where supported. Application compiles SQL and verifies totals, weighted denominators, coverage and descriptive contributions; publishes report directly. Prefer this over run_sql for period comparisons. Unknown periods require clarification.",
            "strict": True,
            "parameters": comparison_schema(),
        },
        definition(
            "list_tables", "List authorized relations and bounded metadata", {}, []
        ),
        definition(
            "describe_table",
            "Describe one authorized relation",
            {"name": {"type": "string"}},
            ["name"],
        ),
        definition(
            "preview",
            "Preview up to 20 authorized rows",
            {"name": {"type": "string"}, "limit": {"type": "integer"}},
            ["name", "limit"],
        ),
        definition(
            "record_plan",
            "Declare public metric assumptions and validation checks before executing",
            {
                "objective": {"type": "string"},
                "metric_ids": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "checks": {"type": "array", "items": {"type": "string"}},
            },
            ["objective", "metric_ids", "assumptions", "checks"],
        ),
        definition(
            "run_sql",
            "Execute a bounded read-only analytical query",
            {"sql": {"type": "string"}},
            ["sql"],
        ),
        definition(
            "finish",
            "Submit a query-backed answer or refuse unsupported/unsafe analysis",
            {
                "answer": {"type": "string"},
                "sql": {"type": "string"},
                "chart": {"type": "string", "enum": ["bar", "line", "table"]},
                "refused": {"type": "boolean"},
            },
            ["answer", "sql", "chart", "refused"],
        ),
    ]


def comparison_schema():
    from app.analytics.semantic import ComparisonRequest

    return ComparisonRequest.model_json_schema()
