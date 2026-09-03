from app.agent.intents import classify
from app.agent.llm import StubLLM
from app.agent.planner import Planner
from app.eval.golden import GOLDEN, run_golden


def _compact_sql(sql: str) -> str:
    return " ".join(sql.lower().split())


def test_stub_execution_accuracy(db_session):
    report = run_golden(db_session, llm=StubLLM())
    assert report.n >= 12
    assert report.score >= 0.66, [row for row in report.results if not row.passed]
    assert report.score == 1.0, [(row.id, row.detail) for row in report.results if not row.passed]


def test_compiler_sql_is_not_a_copy_of_the_gold_string():
    """Compiler SQL must not be a copy of the gold strings."""
    copies = []
    for gold in GOLDEN:
        if not gold.sql:
            continue
        intent = classify(gold.question)
        assert intent is not None, gold.id
        assert intent.sql, gold.id
        if _compact_sql(intent.sql) == _compact_sql(gold.sql):
            copies.append(gold.id)
    assert copies == []


def test_stub_walks_the_tool_loop(db_session):
    result = Planner(db_session, llm=StubLLM()).run("Revenue by family")
    assert not result.refused
    assert result.attempts >= 1


def test_drop_question_is_refused(db_session):
    result = Planner(db_session, llm=StubLLM()).run("drop table fact_sales")
    assert result.refused
    assert result.rows == []


def test_stub_answers_revenue_by_family(db_session):
    result = Planner(db_session, llm=StubLLM()).run("Revenue by family")
    assert not result.refused
    assert result.sql
    assert len(result.rows) >= 1
    assert result.chart == "bar"
