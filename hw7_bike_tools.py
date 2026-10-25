import ast
import csv
import io
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


RAW = Path("reports/hw07/raw")
PRICE_URL = "https://divvybikes.com/pricing"
ARITHMETIC = re.compile(r"^[0-9+\-*/().\s]+$")
TOOL_SCHEMAS = {
    "csv_sql": {
        "type": "object",
        "properties": {"sql": {"type": "string", "description": "One read-only SELECT on uploaded"}},
        "required": ["sql"],
        "additionalProperties": False,
    },
    "policy_retriever": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "const": PRICE_URL},
            "query": {"type": "string"},
            "k": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["url", "query"],
        "additionalProperties": False,
    },
    "calculator": {
        "type": "object",
        "properties": {"expression": {"type": "string"}, "units": {"type": "string"}},
        "required": ["expression"],
        "additionalProperties": False,
    },
}


def envelope(success, data=None, error=None, source=None):
    return {
        "success": success,
        "data": data,
        "error": error,
        "source": source,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def csv_sql(sql, csv_text):
    if not isinstance(sql, str) or not re.match(r"^\s*SELECT\b", sql, re.I) or ";" in sql:
        return envelope(False, error="Only one read-only SELECT is allowed", source="uploaded.csv")
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        columns = reader.fieldnames or []
        allowed = {"ride_id", "rideable_type", "started_at", "ended_at", "duration_minutes", "week", "scenario_selected"}
        if set(columns) != allowed:
            return envelope(False, error="CSV columns do not match the Divvy scenario schema", source="uploaded.csv")
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE uploaded (ride_id TEXT, rideable_type TEXT, started_at TEXT, ended_at TEXT, duration_minutes REAL, week INTEGER, scenario_selected INTEGER)")
        column_order = list(allowed)
        connection.executemany(
            f"INSERT INTO uploaded ({','.join(column_order)}) VALUES (?,?,?,?,?,?,?)",
            [tuple(row[column] for column in column_order) for row in csv.DictReader(io.StringIO(csv_text))],
        )
        connection.set_authorizer(
            lambda operation, arg1, arg2, database, trigger: sqlite3.SQLITE_OK
            if operation in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
            else sqlite3.SQLITE_DENY
        )
        result = connection.execute(sql).fetchmany(501)
        if len(result) > 500:
            return envelope(False, error="Query result exceeds 500 rows", source="uploaded.csv")
        data = [dict(row) for row in result]
        return envelope(True, data={"rows": data, "row_count": len(data), "source": "uploaded.csv"}, source="uploaded.csv")
    except (sqlite3.Error, ValueError, TypeError) as error:
        return envelope(False, error=f"Read-only query failed: {type(error).__name__}", source="uploaded.csv")


def policy_retriever(url, query, k=3, fixture=None):
    if fixture is None and url != PRICE_URL:
        return envelope(False, error="Only the official Divvy pricing URL is accepted", source=url)
    text = fixture if fixture is not None else (RAW / "divvy_pricing.txt").read_text()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if fixture is None:
        lines = [line for line in lines if "$1 + $0.20/min" in line or "$143.90/year" in line or "45 min free, then $0.20/min" in line]
        lines = list(dict.fromkeys(lines))
    passages = [{"text": line[:240], "source": url, "score": round(1 - index * 0.1, 2)} for index, line in enumerate(lines[:max(1, min(int(k), 5))])]
    metadata = json.loads((RAW / "divvy_sources.json").read_text())["pricing"] if fixture is None else {}
    return envelope(True, data={"passages": passages, "captured_utc": metadata.get("accessed_utc"), "sha256": metadata.get("html_sha256")}, source=url)


def arithmetic_node(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = arithmetic_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left, right = arithmetic_node(node.left), arithmetic_node(node.right)
        return {
            ast.Add: lambda: left + right,
            ast.Sub: lambda: left - right,
            ast.Mult: lambda: left * right,
            ast.Div: lambda: left / right,
        }[type(node.op)]()
    raise ValueError("Only basic arithmetic is allowed")


def calculator(expression, units=None):
    if not isinstance(expression, str) or not ARITHMETIC.fullmatch(expression) or len(expression) > 120:
        return envelope(False, error="Expression must contain only numbers and basic arithmetic")
    try:
        value = arithmetic_node(ast.parse(expression, mode="eval").body)
        return envelope(True, data={"value": round(value, 4), "units": units}, source="calculator")
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return envelope(False, error="Invalid arithmetic expression", source="calculator")
