"""Strict CSV ingestion and bounded request handling; no global dataset storage."""
import asyncio
import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

BODY_LIMIT = 1_000_000
CSV_LIMIT = 400_000
MAX_ROWS = 5000


class UploadProblem(ValueError):
    """Recoverable client issue, with record/column locations and no cell values."""
    def __init__(self, message, *, code="invalid_file", issues=None, hint="Review the file and try again."):
        super().__init__(message)
        self.code, self.issues, self.hint = code, (issues or [])[:20], hint

    def response(self):
        return {"detail": str(self), "code": self.code, "issues": self.issues, "hint": self.hint}


class Upload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    csv: str = Field(min_length=1, max_length=CSV_LIMIT)
    mapping: dict[str, str] = Field(default_factory=dict, max_length=20)
    options: dict[str, str] = Field(default_factory=dict, max_length=12)
    review: str = Field(default="", max_length=4000)


    @field_validator("mapping", "options")
    @classmethod
    def bounded_contract(cls, value):
        if any(len(k) > 40 or len(v) > 120 for k, v in value.items()):
            raise ValueError("Contract labels and values exceed their bounds")
        return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse(source):
    if len(source.encode("utf-8")) > CSV_LIMIT:
        raise ValueError("CSV exceeds 400 KB; use a smaller export")
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in source):
        raise ValueError("CSV contains unsupported control characters")
    try:
        reader = csv.reader(io.StringIO(source.lstrip("\ufeff"), newline=""), strict=True)
        headers = next(reader)
        if not 1 <= len(headers) <= 60 or any(not h.strip() or len(h) > 120 for h in headers):
            raise ValueError("CSV needs 1–60 named columns, each at most 120 characters")
        if len({h.strip().casefold() for h in headers}) != len(headers):
            raise UploadProblem("Duplicate column names are ambiguous", code="duplicate_headers",
                                issues=[{"row": 1, "column": name, "message": "This header is repeated."}
                                        for name in headers if sum(h.strip().casefold() == name.strip().casefold() for h in headers) > 1],
                                hint="Give each column a unique name in the header row, then upload the corrected file.")
        rows = []
        for number, row in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise ValueError("CSV exceeds 5,000 records")
            if len(row) != len(headers) or any(len(cell) > 2048 for cell in row):
                raise UploadProblem(f"CSV row {number} has an invalid column count or oversized field",
                                    code="invalid_record", issues=[{"row": number, "column": "", "message": f"Expected {len(headers)} fields, each at most 2,048 characters."}],
                                    hint="Check the highlighted record's comma separators, quoting and field lengths.")
            rows.append(row)
        if not rows:
            raise ValueError("CSV has no records")
    except (csv.Error, StopIteration):
        raise ValueError("Invalid CSV; upload a UTF-8 comma-separated file with a header") from None
    return headers, rows


def profile(source):
    headers, rows = parse(source)
    def numeric(value):
        try:
            decimal_value(value)
            return True
        except ValueError:
            return False
    return {"rows": len(rows), "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "columns": [{"id": f"c{i}", "name": name,
                         "missing": sum(not row[i].strip() for row in rows),
                         "distinct": len({row[i] for row in rows}),
                         "numeric": sum(numeric(row[i]) for row in rows),
                         "samples": [row[i][:100] for row in rows[:3]]}
                        for i, name in enumerate(headers)],
            "preview": [{"row": i+2, "cells": row} for i, row in enumerate(rows[:10])]}


class Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    csv: str = Field(min_length=1, max_length=CSV_LIMIT)
    offset: int = Field(default=0, ge=0, le=MAX_ROWS)
    search: str = Field(default="", max_length=120)
    rows: list[int] = Field(default_factory=list, max_length=20)


def preview(request):
    headers, rows = parse(request.csv)
    if any(type(n) is not int or n < 1 or n > MAX_ROWS+1 for n in request.rows):
        raise ValueError("Invalid record selection")
    selected = [{"row": i+2, "cells": row} for i, row in enumerate(rows)
                if (not request.rows or i+2 in request.rows)
                and (not request.search or any(request.search.casefold() in cell.casefold() for cell in row))]
    return {"headers": headers, "rows": selected[request.offset:request.offset+25], "matches": len(selected), "total": len(rows)}


def column(mapping, name, headers, optional=False):
    value = mapping.get(name, "")
    if optional and not value:
        return None
    if not re.fullmatch(r"c\d{1,2}", value) or int(value[1:]) >= len(headers):
        raise ValueError(f"Choose a valid column for {name}")
    return int(value[1:])


def decimal_value(value, *, places=6, nonnegative=False):
    if not re.fullmatch(r"-?\d{1,12}(?:\.\d{1,6})?", value.strip()):
        raise ValueError("Numbers must be plain decimals without currency symbols, commas or exponents")
    try:
        number = Decimal(value.strip())
        if number.as_tuple().exponent < -places or (nonnegative and number < 0):
            raise ValueError("Number precision or sign violates the selected contract")
        if abs(number) > 100_000_000:
            raise ValueError("Individual numeric value exceeds the supported bound")
        return number
    except InvalidOperation:
        raise ValueError("Invalid number") from None


def integer(value):
    return int(decimal_value(value, places=0, nonnegative=True))


def safe_csv(headers, rows):
    """Quote formula-like text, preserving typed numeric values as numbers."""
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([safe(h) for h in headers])
    writer.writerows([[safe(v) for v in row] for row in rows])
    return stream.getvalue()


class UploadBoundary:
    """Enforce actual streamed bytes before JSON parsing, including chunked bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(("/api/uploads/", "/api/account/")):
            return await self.app(scope, receive, send)
        if scope["method"] == "POST":
            headers = dict(scope.get("headers", []))
            if headers.get(b"content-type", b"").split(b";")[0] != b"application/json":
                return await JSONResponse({"detail": "JSON upload transport required"}, 415)(scope, receive, send)
            chunks, size = [], 0
            try:
                async with asyncio.timeout(15):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        size += len(chunk)
                        if size > BODY_LIMIT:
                            return await JSONResponse({"detail": "Upload request exceeds 1 MB"}, 413)(scope, receive, send)
                        chunks.append(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await JSONResponse({"detail": "Upload timed out"}, 408)(scope, receive, send)
            body = b"".join(chunks)
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)
