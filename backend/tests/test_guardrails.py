from app.agent.guardrails import GuardrailError, validate_sql
from app.agent.tools import WarehouseTools


def test_rejects_drop():
    try:
        validate_sql("DROP TABLE fact_sales")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_insert():
    try:
        validate_sql("INSERT INTO fact_sales (date_id, sku_id, dc_id, units, revenue_usd) VALUES (1,1,1,1,1)")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_update():
    try:
        validate_sql("UPDATE fact_sales SET units = 0")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_delete():
    try:
        validate_sql("DELETE FROM fact_sales")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_multiple_statements():
    try:
        validate_sql("SELECT 1; DROP TABLE fact_sales")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_comment_block_smuggling():
    try:
        validate_sql("SELECT 1 /* DROP TABLE fact_sales */")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_line_comment_smuggling():
    try:
        validate_sql("SELECT 1 -- DROP TABLE fact_sales")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass


def test_rejects_alter_and_pragma():
    for sql in ("ALTER TABLE fact_sales DROP COLUMN units", "PRAGMA foreign_keys=OFF"):
        try:
            validate_sql(sql)
            raise AssertionError(f"expected GuardrailError for {sql}")
        except GuardrailError:
            pass


def test_allows_select(db_session):
    sql = validate_sql("SELECT sku_code, family FROM dim_sku ORDER BY sku_id LIMIT 5")
    tools = WarehouseTools(db_session)
    columns, rows = tools.run_sql(sql)
    assert columns[0] == "sku_code"
    assert len(rows) == 5


def test_allows_cte():
    rewritten = validate_sql("WITH x AS (SELECT 1 AS n) SELECT n FROM x")
    assert rewritten.upper().startswith("WITH")


def test_select_star_without_limit_is_capped():
    rewritten = validate_sql("SELECT * FROM dim_sku")
    assert "LIMIT 500" in rewritten.upper()


def test_limit_above_cap_is_rewritten():
    rewritten = validate_sql("SELECT sku_code FROM dim_sku LIMIT 9999")
    assert "LIMIT 500" in rewritten.upper()


def test_run_sql_is_only_execution_path(db_session):
    tools = WarehouseTools(db_session)
    try:
        tools.run_sql("UPDATE fact_sales SET units = 0")
        raise AssertionError("expected GuardrailError")
    except GuardrailError:
        pass
    before = db_session.execute(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM fact_sales")
    ).scalar_one()
    assert before > 0
