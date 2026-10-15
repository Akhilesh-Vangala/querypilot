# QueryPilot tests

Tests are grouped by the responsibility they exercise. API, agent, analytics/verification, persistence and workflow directories may contain both isolated and integration checks; their names do not claim external dependencies are mocked. The root conftest.py provides the shared database/session fixtures. Live model quality remains a separate evaluation gate.

Run `python -m pytest -q backend/tests` from the repository root.
