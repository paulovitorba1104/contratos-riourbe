from datetime import date

import httpx

from app.core import bcb_sgs


class _RespostaFalsa:
    def __init__(self, status_code: int, corpo):
        self.status_code = status_code
        self._corpo = corpo

    def json(self):
        return self._corpo


def test_consultar_indice_ipca_e_compoe_variacoes_mensais(monkeypatch):
    # Marco em 13/06/2022, data-base em 13/06/2021 — janela consultada:
    # jul/2021 a jun/2022 (12 meses), variações fictícias de 0,5% cada.
    monkeypatch.setattr(
        bcb_sgs.httpx,
        "get",
        lambda url, params, timeout: _RespostaFalsa(200, [{"data": "01/07/2021", "valor": "0.50"}] * 12),
    )
    resultado = bcb_sgs.consultar_indice("ipca_e", date(2021, 6, 13), date(2022, 6, 13))
    assert resultado is not None
    assert resultado["indice_base"] == 1000.0
    # 1000 * 1.005**12 ≈ 1061.678...
    assert abs(resultado["indice_atual"] - 1000 * 1.005**12) < 0.001


def test_consultar_indice_retorna_none_para_indice_nao_suportado():
    assert bcb_sgs.consultar_indice("igp_m", date(2021, 1, 1), date(2022, 1, 1)) is None


def test_consultar_indice_retorna_none_quando_data_atual_nao_e_posterior():
    assert bcb_sgs.consultar_indice("ipca_e", date(2022, 6, 13), date(2022, 6, 13)) is None
    assert bcb_sgs.consultar_indice("ipca_e", date(2022, 6, 13), date(2021, 6, 13)) is None


def test_consultar_indice_retorna_none_quando_api_indisponivel(monkeypatch):
    def _levanta(url, params, timeout):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(bcb_sgs.httpx, "get", _levanta)
    assert bcb_sgs.consultar_indice("ipca_e", date(2021, 6, 13), date(2022, 6, 13)) is None


def test_consultar_indice_retorna_none_quando_status_diferente_de_200(monkeypatch):
    monkeypatch.setattr(bcb_sgs.httpx, "get", lambda url, params, timeout: _RespostaFalsa(404, []))
    assert bcb_sgs.consultar_indice("ipca_e", date(2021, 6, 13), date(2022, 6, 13)) is None


def test_consultar_indice_retorna_none_quando_resposta_e_inesperada(monkeypatch):
    monkeypatch.setattr(bcb_sgs.httpx, "get", lambda url, params, timeout: _RespostaFalsa(200, {"erro": "algo"}))
    assert bcb_sgs.consultar_indice("ipca_e", date(2021, 6, 13), date(2022, 6, 13)) is None


def test_consultar_indice_sem_variacoes_no_periodo_mantem_indice_base(monkeypatch):
    monkeypatch.setattr(bcb_sgs.httpx, "get", lambda url, params, timeout: _RespostaFalsa(200, []))
    resultado = bcb_sgs.consultar_indice("ipca_e", date(2021, 6, 13), date(2022, 6, 13))
    assert resultado == {"indice_base": 1000.0, "indice_atual": 1000.0}


def test_consultar_indice_reajuste_usa_mes_anterior_as_duas_datas(monkeypatch):
    """Cláusula-padrão: Io é o índice do mês ANTERIOR à apresentação da
    proposta, I é o índice do mês anterior ao aniversário — não o índice do
    próprio mês de referência. Proposta em 28/03/2022 (mês anterior:
    fevereiro) e aniversário em 14/05/2024 (mês anterior: abril) devem
    consultar o SGS na janela de março/2022 a abril/2024."""
    chamadas = []

    def _capturar(url, params, timeout):
        chamadas.append(params)
        return _RespostaFalsa(200, [])

    monkeypatch.setattr(bcb_sgs.httpx, "get", _capturar)
    resultado = bcb_sgs.consultar_indice_reajuste("ipca_e", date(2022, 3, 28), date(2024, 5, 14))

    assert resultado == {"indice_base": 1000.0, "indice_atual": 1000.0}
    assert len(chamadas) == 1
    assert chamadas[0]["dataInicial"] == "01/03/2022"
    assert chamadas[0]["dataFinal"] == "01/04/2024"


def test_consultar_indice_reajuste_retorna_none_quando_indisponivel(monkeypatch):
    def _levanta(url, params, timeout):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(bcb_sgs.httpx, "get", _levanta)
    assert bcb_sgs.consultar_indice_reajuste("ipca_e", date(2022, 3, 28), date(2024, 5, 14)) is None


def test_consultar_indice_reajuste_reproduz_exemplo_1_da_calculadora_do_cidadao(monkeypatch):
    """A "Metodologia da Correção pelos Índices" da própria Calculadora do
    Cidadão do Banco Central traz, como Exemplo 1: correção pelo IPCA de um
    único mês (data inicial = data final = 01/2003) usa a variação daquele
    mês sozinho — í­ndice de correção 1,0225 (IPCA de jan/2003 = 2,25%).

    Isso só acontece com um único mês consultado quando o aniversário do
    reajuste cai exatamente 1 mês depois da apresentação da proposta (mês
    anterior ao aniversário = mês da própria apresentação da proposta,
    fechando a janela num mês só)."""
    chamadas = []

    def _capturar(url, params, timeout):
        chamadas.append(params)
        return _RespostaFalsa(200, [{"data": "01/01/2003", "valor": "2.25"}])

    monkeypatch.setattr(bcb_sgs.httpx, "get", _capturar)
    resultado = bcb_sgs.consultar_indice_reajuste("ipca_e", date(2003, 1, 20), date(2003, 2, 10))

    assert chamadas[0]["dataInicial"] == "01/01/2003"
    assert chamadas[0]["dataFinal"] == "01/01/2003"
    assert resultado is not None
    assert abs(resultado["indice_atual"] / resultado["indice_base"] - 1.0225) < 1e-9


def test_consultar_indice_reajuste_reproduz_janela_do_exemplo_2_da_calculadora_do_cidadao(monkeypatch):
    """Exemplo 2 da mesma metodologia oficial: correção de 01/2003 a
    12/2003 usa os 12 meses do ano, ambos os extremos inclusive (janeiro a
    dezembro). O valor exato do exemplo (índice 1,0929994) depende das
    variações reais do IPCA em 2003, que este teste não tem como conferir
    sem acesso à série do Banco Central — o que dá para verificar aqui, com
    variações fictícias, é que a JANELA consultada bate com a do exemplo:
    12 meses, de janeiro a dezembro de 2003, quando o aniversário do
    reajuste cai 12 meses depois da apresentação da proposta."""
    chamadas = []
    variacoes_fake = [0.5] * 12

    def _capturar(url, params, timeout):
        chamadas.append(params)
        return _RespostaFalsa(200, [{"data": "01/01/2003", "valor": str(v)} for v in variacoes_fake])

    monkeypatch.setattr(bcb_sgs.httpx, "get", _capturar)
    resultado = bcb_sgs.consultar_indice_reajuste("ipca_e", date(2003, 1, 20), date(2004, 1, 10))

    assert chamadas[0]["dataInicial"] == "01/01/2003"
    assert chamadas[0]["dataFinal"] == "01/12/2003"
    assert resultado is not None
    fator = resultado["indice_atual"] / resultado["indice_base"]
    assert abs(fator - 1.005**12) < 1e-6
