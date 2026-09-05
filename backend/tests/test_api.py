def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["checks"]["database"] is True


def test_token_and_me(client, analyst_headers):
    me = client.get("/api/auth/me", headers=analyst_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "analyst@querypilot.example.com"
    assert body["role"] == "analyst"


def test_bad_password(client):
    response = client.post(
        "/api/auth/token",
        data={"username": "analyst@querypilot.example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_schema_requires_auth(client, analyst_headers):
    assert client.get("/api/schema").status_code == 401
    response = client.get("/api/schema", headers=analyst_headers)
    assert response.status_code == 200
    names = {table["name"] for table in response.json()["tables"]}
    assert "fact_claims" in names
    assert "dim_provider" in names


def test_ask_and_history(client, analyst_headers):
    asked = client.post(
        "/api/ask",
        json={"question": "Claims paid by specialty"},
        headers=analyst_headers,
    )
    assert asked.status_code == 200
    body = asked.json()
    assert body["refused"] is False
    assert body["sql"]
    assert body["rows"]
    assert "answer" in body

    history = client.get("/api/ask/history", headers=analyst_headers)
    assert history.status_code == 200
    items = history.json()
    assert len(items) >= 1
    assert items[0]["question"] == "Claims paid by specialty"


def test_ask_refuses_drop(client, analyst_headers):
    response = client.post(
        "/api/ask",
        json={"question": "drop table fact_claims"},
        headers=analyst_headers,
    )
    assert response.status_code == 200
    assert response.json()["refused"] is True


def test_eval_admin_only(client, analyst_headers, admin_headers):
    forbidden = client.post("/api/eval/run", headers=analyst_headers)
    assert forbidden.status_code == 403
    allowed = client.post("/api/eval/run", headers=admin_headers)
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["n"] >= 12
    assert body["score"] >= 0.66
