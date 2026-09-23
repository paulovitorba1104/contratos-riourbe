"""Consulta gratuita de CNPJ na BrasilAPI (sem chave/autenticação —
https://brasilapi.com.br/api/cnpj/v1/{cnpj}, que por sua vez espelha os
dados públicos da Receita Federal), usada ao cadastrar/editar fornecedor
para conferir a situação cadastral e sugerir a razão social."""

import logging

import httpx

logger = logging.getLogger(__name__)

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def consultar_cnpj(cnpj: str) -> dict | None:
    """Retorna {"situacao_cadastral": ..., "razao_social": ...} quando a
    BrasilAPI responde, ou None quando a consulta não pôde ser feita (API
    indisponível, timeout, CNPJ não encontrado) — verificação de melhor
    esforço sobre uma API externa gratuita, então uma falha de consulta não
    deve travar o cadastro nem o autopreenchimento."""
    try:
        resposta = httpx.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=5.0)
    except httpx.HTTPError:
        logger.warning("Não foi possível consultar o CNPJ %s na BrasilAPI.", cnpj)
        return None
    if resposta.status_code != 200:
        return None
    corpo = resposta.json()
    return {
        "situacao_cadastral": corpo.get("descricao_situacao_cadastral"),
        "razao_social": corpo.get("razao_social"),
    }


def consultar_situacao_cnpj(cnpj: str) -> str | None:
    """Atalho só com a situação cadastral — usado na validação de "CNPJ
    ativo" ao salvar."""
    resultado = consultar_cnpj(cnpj)
    return resultado["situacao_cadastral"] if resultado else None
