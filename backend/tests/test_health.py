from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_headers_de_seguranca_presentes():
    resposta = client.get("/health")
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-frame-options"] == "DENY"
    assert resposta.headers["cache-control"] == "no-store"
