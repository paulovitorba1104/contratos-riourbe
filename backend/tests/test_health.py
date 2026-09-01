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


def test_raiz_sem_build_do_frontend_retorna_json():
    """Sem app/static (build do frontend), a raiz cai no fallback JSON —
    é o que acontece em dev local, quando o frontend roda em outro processo."""
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert resposta.json()["sistema"]
