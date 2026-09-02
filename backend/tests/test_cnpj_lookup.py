import httpx

from app.core import cnpj_lookup


class _RespostaFalsa:
    def __init__(self, status_code: int, corpo: dict):
        self.status_code = status_code
        self._corpo = corpo

    def json(self) -> dict:
        return self._corpo


def test_consultar_situacao_retorna_descricao_quando_api_responde(monkeypatch):
    monkeypatch.setattr(
        cnpj_lookup.httpx,
        "get",
        lambda url, timeout: _RespostaFalsa(200, {"descricao_situacao_cadastral": "ATIVA"}),
    )
    assert cnpj_lookup.consultar_situacao_cnpj("11222333000181") == "ATIVA"


def test_consultar_situacao_retorna_none_quando_api_falha(monkeypatch):
    def _levanta(url, timeout):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(cnpj_lookup.httpx, "get", _levanta)
    assert cnpj_lookup.consultar_situacao_cnpj("11222333000181") is None


def test_consultar_situacao_retorna_none_quando_status_diferente_de_200(monkeypatch):
    monkeypatch.setattr(cnpj_lookup.httpx, "get", lambda url, timeout: _RespostaFalsa(404, {}))
    assert cnpj_lookup.consultar_situacao_cnpj("11222333000181") is None
