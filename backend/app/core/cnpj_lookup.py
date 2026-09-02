"""Consulta gratuita da situação cadastral de um CNPJ na BrasilAPI (sem
chave/autenticação — https://brasilapi.com.br/api/cnpj/v1/{cnpj}), usada ao
cadastrar/editar fornecedor para conferir se o CNPJ está ativo na Receita
Federal antes de salvar."""

import logging

import httpx

logger = logging.getLogger(__name__)

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def consultar_situacao_cnpj(cnpj: str) -> str | None:
    """Retorna a descrição da situação cadastral (ex.: "ATIVA") quando a
    BrasilAPI responde, ou None quando a consulta não pôde ser feita (API
    indisponível, timeout, CNPJ não encontrado) — verificação de melhor
    esforço sobre uma API externa gratuita, então uma falha de consulta não
    deve travar o cadastro."""
    try:
        resposta = httpx.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=5.0)
    except httpx.HTTPError:
        logger.warning("Não foi possível consultar a situação cadastral do CNPJ %s na BrasilAPI.", cnpj)
        return None
    if resposta.status_code != 200:
        return None
    return resposta.json().get("descricao_situacao_cadastral")
