"""Reviewed aggregate analytics on request-scoped customer CSVs."""
import hashlib
import sqlite3
from collections import defaultdict
from decimal import Decimal, localcontext

from .ingestion import column, decimal_value, fingerprint, parse, safe_csv


def run(upload):
    headers, rows = parse(upload.csv)
    if set(upload.mapping) - {"measure", "group", "filter"} or set(upload.options) - {"operation", "filter_value"}:
        raise ValueError("Unsupported analytical contract fields")
    operation = upload.options.get("operation", "sum")
    if operation not in ("sum", "count", "average"):
        raise ValueError("Choose sum, count or average")
    measure = column(upload.mapping, "measure", headers, operation == "count")
    group = column(upload.mapping, "group", headers, True)
    filter_col = column(upload.mapping, "filter", headers, True)
    wanted = upload.options.get("filter_value", "")
    if filter_col is None and wanted:
        raise ValueError("Select a filter column before setting a filter value")
    included, reference = [], defaultdict(list)
    for row in rows:
        if filter_col is not None and row[filter_col] != wanted:
            continue
        value = Decimal(1) if operation == "count" else decimal_value(row[measure])
        label = row[group] if group is not None else "All records"
        reference[label].append(value)
        included.append((label, int(value*1_000_000)))
    if not included:
        raise ValueError("No records match the reviewed filter; no aggregate was invented")
    if len(reference) > 100:
        raise ValueError("More than 100 groups; choose a broader grouping or filter")
    # Integer micro-units avoid floating sum drift. Average uses independently
    # reconciled sum and count; no averaging of averages or guessed missing values.
    sql = "SELECT segment, SUM(value_micro) AS sum_micro, COUNT(*) AS n FROM records GROUP BY segment ORDER BY segment"
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE records(segment TEXT NOT NULL, value_micro INTEGER NOT NULL)")
        db.executemany("INSERT INTO records VALUES (?,?)", included)
        db.execute("PRAGMA query_only=ON")
        observed = list(db.execute(sql))
    results, checks = [], {}
    with localcontext() as ctx:
        ctx.prec = 38
        for label, total_micro, n in observed:
            expected_sum = sum(reference[label], Decimal(0))
            checks[label] = Decimal(total_micro)/1_000_000 == expected_sum and n == len(reference[label])
            value = Decimal(n) if operation == "count" else expected_sum
            if operation == "average":
                value /= n
            results.append({"segment": label, "value": format(value, "f"), "records": n})
    if not all(checks.values()) or len(observed) != len(reference):
        raise ValueError("Independent reconciliation failed; results withheld")
    return {"project": "QueryPilot", "mode": "reviewed-aggregate", "live_ai": False,
            "source_sha256": hashlib.sha256(upload.csv.encode()).hexdigest(), "contract": {"mapping": upload.mapping, "options": upload.options},
            "summary": {"source_rows": len(rows), "included_rows": len(included), "groups": len(results), "operation": operation},
            "checks": {"sql_sums_and_counts_match_decimal_reference": all(checks.values())},
            "results": results, "sql": sql,
            "column_bindings": {"segment": headers[group] if group is not None else "constant All records",
                                "value_micro": "1,000,000 × " + (headers[measure] if operation != "count" else "constant 1")},
            "csv": safe_csv(["segment", "value", "records"], [[r["segment"], Decimal(r["value"]), r["records"]] for r in results]),
            "scope": "Read-only analytics for the explicitly selected measure, grouping and exact-match filter. Missing or invalid included numeric values refuse the request. No causal inference or live language interpretation.",
            "activity": ["profile-upload", "review-metric-contract", "compile-typed-aggregate", "execute-in-memory", "independent-decimal-reconciliation", "export-evidence"]}
