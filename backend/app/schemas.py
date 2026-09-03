from datetime import datetime

from pydantic import BaseModel, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    email: str
    full_name: str
    role: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str
    sql: str
    chart: str
    rows: list[list]
    columns: list[str]
    attempts: int
    refused: bool


class HistoryItem(BaseModel):
    id: int
    question: str
    sql: str
    answer: str
    refused: bool
    created_at: datetime


class ColumnInfo(BaseModel):
    name: str
    type: str


class TableInfo(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnInfo]


class SchemaOut(BaseModel):
    tables: list[TableInfo]


class EvalCaseResult(BaseModel):
    id: str
    question: str
    passed: bool
    refused: bool
    predicted_sql: str = ""
    detail: str = ""


class EvalReportOut(BaseModel):
    score: float
    n: int
    passed: int
    results: list[EvalCaseResult]
