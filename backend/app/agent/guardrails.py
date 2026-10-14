"""AST and scope checks form an allowlist, not a keyword permission boundary."""

from __future__ import annotations
import re
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope
from .catalog import WAREHOUSE_TABLES

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
FUNCTIONS = {
    "SUM",
    "AVG",
    "COUNT",
    "MIN",
    "MAX",
    "ROUND",
    "COALESCE",
    "NULLIF",
    "CAST",
    "TRY_CAST",
    "ABS",
    "FLOOR",
    "CEIL",
    "LOWER",
    "UPPER",
    "LENGTH",
    "EXTRACT",
    "DATE_TRUNC",
    "GREATEST",
    "LEAST",
    "ROW_NUMBER",
    "RANK",
    "DENSE_RANK",
    "LAG",
    "LEAD",
    "IF",
    "CASE",
    "CONCAT",
    "SUBSTRING",
    "TRIM",
}


class GuardrailError(ValueError):
    pass


def validate_sql(
    sql: str, *, max_rows: int = MAX_ROWS, dialect: str | None = None
) -> str:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 24000:
        raise GuardrailError("SQL must be nonempty and within the size limit")
    # Keep legacy comment-smuggling refusal; comments can never grant permissions.
    for comment in re.findall(r"/\*.*?\*/|--[^\n]*", sql, flags=re.S):
        if re.search(r"\b(?:" + "|".join(FORBIDDEN) + r")\b", comment, flags=re.I):
            raise GuardrailError("comment contains a forbidden keyword")
    try:
        trees = sqlglot.parse(sql, read=dialect)
    except sqlglot.errors.ParseError:
        raise GuardrailError("SQL could not be parsed") from None
    trees = [tree for tree in trees if tree is not None]
    if len(trees) != 1 or not isinstance(trees[0], (exp.Select, exp.SetOperation)):
        raise GuardrailError("Only a single read-only query is allowed")
    tree = trees[0]
    if len(list(tree.walk())) > 1600:
        raise GuardrailError("SQL expression exceeds the complexity limit")
    forbidden_types = (exp.DDL, exp.DML, exp.Command, exp.Into, exp.Lock)
    if any(isinstance(node, forbidden_types) for node in tree.walk()):
        raise GuardrailError("Writes, commands and locking reads are forbidden")
    for with_node in tree.find_all(exp.With):
        if with_node.args.get("recursive"):
            raise GuardrailError("Recursive queries are outside the analytical budget")
    for function in tree.find_all(exp.Func):
        name = (
            function.name.upper()
            if isinstance(function, exp.Anonymous)
            else function.sql_name()
        )
        if name not in FUNCTIONS:
            raise GuardrailError("Function is outside the reviewed allowlist: " + name)
    for scope in traverse_scope(tree):
        facts = []
        for _, (_, source) in scope.selected_sources.items():
            if isinstance(source, exp.Table):
                name = source.name.lower()
                if name not in WAREHOUSE_TABLES or source.db or source.catalog:
                    raise GuardrailError("Relation is outside the authorized warehouse")
                if name.startswith("fact_"):
                    facts.append(name)
        if len(facts) > 1:
            raise GuardrailError(
                "Aggregate each fact to a common grain before joining multiple fact tables"
            )
        for join in scope.expression.find_all(exp.Join):
            if join.args.get("kind") == "CROSS" or not (
                join.args.get("on") or join.args.get("using")
            ):
                raise GuardrailError(
                    "Cartesian joins are outside the analytical budget"
                )
    # Reject non-table sources (table-valued functions/VALUES) unless they are an owned CTE/subquery.
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise GuardrailError("Table-valued functions are not authorized")
    current_limit = tree.args.get("limit")
    value = current_limit.expression if current_limit else None
    cap = max(1, min(int(max_rows), MAX_ROWS))
    if (
        not isinstance(value, exp.Literal)
        or not value.is_int
        or int(value.this) < 0
        or int(value.this) > cap
    ):
        tree = tree.limit(cap)
    return tree.sql(dialect=dialect)
