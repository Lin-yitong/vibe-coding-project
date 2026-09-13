from fastapi.testclient import TestClient

from app.main import app


def test_application_has_an_openapi_document() -> None:
    client = TestClient(app)
    document = client.get("/openapi.json").json()
    assert document["info"]["title"] == "MewHelp Ch01"


def test_health_check_returns_ok_status() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
