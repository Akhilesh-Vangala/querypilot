from __future__ import annotations

import re

MAX_ROWS = 500

FORBIDDEN = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "COPY",
    "ATTACH",
    "PRAGMA",
    "CREATE",
    "REPLACE",
    "REVOKE",
    "VACUUM",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "INTO",
)

_FORBIDDEN_RE = re.compile(
    r"\b(?:" + "|".join(FORBIDDEN) + r")\b",
    re.IGNORECASE,
)
_SELECT_STAR_RE = re.compile(r"(?is)(?:^|\s)SELECT\s+\*")
_LIMIT_RE = re.compile(r"(?is)\bLIMIT\s+(\d+)")
_BLOCKED_RELATIONS_RE = re.compile(r"\b(?:users|ask_logs)\b", re.IGNORECASE)


class GuardrailError(ValueError):
    pass


def _extract_comments(sql: str) -> list[str]:
    comments = re.findall(r"/\*.*?\*/", sql, flags=re.DOTALL)
    comments.extend(re.findall(r"--.*?$", sql, flags=re.MULTILINE))
    return comments


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql


def _strip_strings(sql: str) -> str:
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    return sql


def validate_sql(sql: str, *, max_rows: int = MAX_ROWS) -> str:
    if not sql or not sql.strip():
        raise GuardrailError("empty SQL")

    raw = sql.strip()
    for comment in _extract_comments(raw):
        if _FORBIDDEN_RE.search(comment):
            raise GuardrailError("comment contains a forbidden keyword")

    stripped = _strip_comments(raw)
    statements = [part.strip() for part in stripped.split(";") if part.strip()]
    if len(statements) != 1:
        raise GuardrailError("only a single statement is allowed")

    body = statements[0]
    scanned = _strip_strings(body)
    if _FORBIDDEN_RE.search(scanned):
        raise GuardrailError("statement contains a forbidden keyword")
    if _BLOCKED_RELATIONS_RE.search(scanned):
        raise GuardrailError("query may not read application tables")

    leading = body.lstrip().split(None, 1)
    if not leading:
        raise GuardrailError("empty SQL")
    keyword = leading[0].upper()
    if keyword not in {"SELECT", "WITH"}:
        raise GuardrailError("only SELECT or WITH ... SELECT is allowed")
    if "SELECT" not in body.upper():
        raise GuardrailError("CTE must be followed by a SELECT")

    rewritten = body
    limit_match = _LIMIT_RE.search(rewritten)
    if _SELECT_STAR_RE.search(rewritten) and limit_match is None:
        rewritten = f"{rewritten} LIMIT {max_rows}"
        limit_match = _LIMIT_RE.search(rewritten)
    if limit_match and int(limit_match.group(1)) > max_rows:
        rewritten = _LIMIT_RE.sub(f"LIMIT {max_rows}", rewritten, count=1)
    return rewritten
