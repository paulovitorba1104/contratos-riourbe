"""Consulta gratuita de índices de preço no SGS (Sistema Gerenciador de
Séries Temporais) do Banco Central — sem chave/autenticação,
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados, dados que
vêm originalmente do IBGE. Usada na calculadora de reajuste para buscar o
IPCA-E sozinha, em vez de quem calcula ter de digitar os números-índice à
mão a partir de uma tabela externa."""

import logging
from datetime import date

import httpx
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# Série do SGS por índice suportado — mesma fonte oficial da calculadora do
# cidadão do Banco Central. Hoje só o IPCA-E; outros índices comuns em
# contrato público (IPCA, IGP-M, INPC) ficam para quando forem pedidos.
SERIES_INDICE = {
    "ipca_e": 10764,
}

# Base arbitrária do número-índice sintético — o SGS só publica a variação
# percentual mensal, não um número-índice pronto. A razão entre o índice
# sintético em duas datas é idêntica à de um número-índice oficial (o ponto
# de partida não importa, só a variação acumulada entre elas), então
# qualquer base fixa serve — 1000 só por ser redondo e fácil de conferir.
INDICE_BASE_SINTETICO = 1000


def _variacoes_mensais(codigo_serie: int, data_inicial: date, data_final: date) -> list[float] | None:
    """Retorna a lista de variações percentuais mensais publicadas entre as
    duas datas (inclusive), ou None quando a consulta não pôde ser feita —
    API indisponível, timeout, resposta inesperada."""
    try:
        resposta = httpx.get(
            BCB_SGS_URL.format(codigo=codigo_serie),
            params={
                "formato": "json",
                "dataInicial": data_inicial.strftime("%d/%m/%Y"),
                "dataFinal": data_final.strftime("%d/%m/%Y"),
            },
            timeout=8.0,
        )
    except httpx.HTTPError:
        logger.warning("Não foi possível consultar a série %s no SGS do Banco Central.", codigo_serie)
        return None
    if resposta.status_code != 200:
        return None
    try:
        pontos = resposta.json()
        return [float(ponto["valor"]) for ponto in pontos]
    except (ValueError, KeyError, TypeError):
        return None


def consultar_indice(nome_indice: str, data_base: date, data_atual: date) -> dict | None:
    """Número-índice sintético (base 1000) na data-base e na data atual do
    reajuste, a partir da variação mensal acumulada entre os dois meses.
    None quando o índice não é suportado, o período é inválido, ou a
    consulta falha — melhor esforço, nunca bloqueia a calculadora manual."""
    codigo_serie = SERIES_INDICE.get(nome_indice)
    if codigo_serie is None or data_atual <= data_base:
        return None

    inicio_janela = date(data_base.year, data_base.month, 1) + relativedelta(months=1)
    fim_janela = date(data_atual.year, data_atual.month, 1)
    variacoes = _variacoes_mensais(codigo_serie, inicio_janela, fim_janela)
    if variacoes is None:
        return None

    indice_atual = float(INDICE_BASE_SINTETICO)
    for variacao in variacoes:
        indice_atual *= 1 + variacao / 100

    return {"indice_base": round(float(INDICE_BASE_SINTETICO), 5), "indice_atual": round(indice_atual, 5)}


def consultar_indice_reajuste(nome_indice: str, data_apresentacao_proposta: date, data_aniversario: date) -> dict | None:
    """Segue a cláusula-padrão de reajuste por IPCA-E (R = Po×[(I-Io)/Io]):
    Io é o índice do mês ANTERIOR ao da apresentação da proposta, e I é o
    índice do mês anterior ao do aniversário do contrato sendo reajustado —
    nunca o índice do próprio mês de referência. Desloca as duas datas um
    mês para trás e delega para `consultar_indice`."""
    return consultar_indice(
        nome_indice,
        data_apresentacao_proposta + relativedelta(months=-1),
        data_aniversario + relativedelta(months=-1),
    )
