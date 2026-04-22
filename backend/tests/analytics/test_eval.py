from app.agents.analytics.llm import StubLLM
from app.agents.analytics.tools import WarehouseTools
from app.evaluation.golden import GOLDEN
from app.evaluation.golden import results_match
from app.evaluation.golden import run_golden


def test_golden_set_size():
    assert len(GOLDEN) >= 12
    assert any(case.must_refuse for case in GOLDEN)


def test_execution_accuracy_harness(db_session):
    report = run_golden(db_session, llm=StubLLM())
    assert report.n >= 12
    assert report.score >= 0.66
    drop = next(row for row in report.results if row.id == "drop_table")
    assert drop.passed
    assert drop.refused


def test_gold_sql_runs(db_session):
    tools = WarehouseTools(db_session)
    for case in GOLDEN:
        if case.must_refuse:
            continue
        columns, rows = tools.run_sql(case.sql)
        assert columns
        assert rows, case.id


def test_results_match_float_tolerance():
    assert results_match([[1.0]], [[1.00005]])
    assert not results_match([[1.0]], [[1.01]])
    assert results_match([["FTW", 10]], [["FTW", 10.0]])
