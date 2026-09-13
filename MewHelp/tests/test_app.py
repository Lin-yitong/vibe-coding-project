from fastapi.testclient import TestClient

from app.main import app


def test_application_has_an_openapi_document() -> None:
    client = TestClient(app)
    document = client.get("/openapi.json").json()
    assert document["info"]["title"] == "MewHelp Ch01"
