from datetime import date
from decimal import Decimal

import pytest

from app.services import reajuste as regras

# Valores exatos da planilha real "Distribuição do Apostilamento - Prédio
# Sede da Rio-Urbe - Contrato 011/2022" enviada pelo usuário — o índice base
# e atual abaixo são sintéticos (a planilha não traz os números brutos do
# IPCA-E, só o resultado), escolhidos para reproduzir a mesma razão I/Io que
# o reajuste real aplicou (130668.67 / 118470.50).
VALOR_ANTIGO = Decimal("118470.50")
INDICE_BASE = Decimal("6500.00")
INDICE_ATUAL = Decimal("7169.264543")
DATA_INICIO = date(2026, 6, 14)
DATA_FIM = date(2027, 6, 13)  # fim da vigência do contrato, meio do mês


def test_valor_mensal_reajustado_bate_com_a_planilha():
    assert regras.calcular_valor_mensal_reajustado(VALOR_ANTIGO, INDICE_ATUAL, INDICE_BASE) == Decimal("130668.67")


def test_indice_base_zero_e_invalido():
    with pytest.raises(regras.PeriodoReajusteInvalido):
        regras.calcular_valor_mensal_reajustado(VALOR_ANTIGO, INDICE_ATUAL, Decimal("0"))


def test_data_fim_antes_da_data_inicio_e_invalido():
    with pytest.raises(regras.PeriodoReajusteInvalido):
        regras.calcular_distribuicao_reajuste(VALOR_ANTIGO, INDICE_ATUAL, INDICE_BASE, DATA_FIM, DATA_INICIO)


def test_distribuicao_bate_linha_a_linha_com_a_planilha_real():
    """A prova de fogo: os 13 meses e o total exatos da planilha real que a
    Rio-Urbe usa para apostilamento — incluindo o pro-rata do primeiro mês
    (reajuste começa em 14/06, no meio do mês) e do último (o contrato
    termina em 13/06/2027, também no meio do mês)."""
    dist = regras.calcular_distribuicao_reajuste(VALOR_ANTIGO, INDICE_ATUAL, INDICE_BASE, DATA_INICIO, DATA_FIM)

    assert dist.valor_mensal_antigo == Decimal("118470.50")
    assert dist.valor_mensal_novo == Decimal("130668.67")
    assert len(dist.linhas) == 13  # jun/2026 até jun/2027, inclusive

    esperado = [
        (date(2026, 6, 1), Decimal("118470.50"), Decimal("125382.80"), Decimal("6912.30")),
        (date(2026, 7, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2026, 8, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2026, 9, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2026, 10, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2026, 11, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2026, 12, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 1, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 2, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 3, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 4, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 5, 1), Decimal("118470.50"), Decimal("130668.67"), Decimal("12198.17")),
        (date(2027, 6, 1), Decimal("51337.22"), Decimal("56623.09"), Decimal("5285.87")),
    ]
    for linha, (competencia, antigo, reajustado, diferenca) in zip(dist.linhas, esperado):
        assert linha.competencia == competencia
        assert linha.valor_antigo == antigo
        assert linha.valor_reajustado == reajustado
        assert linha.diferenca == diferenca

    assert dist.valor_total_apostilamento == Decimal("146378.04")


def test_distribuicao_dentro_de_um_unico_mes_nao_gera_dias_negativos():
    """Marco e fim do período no mesmo mês — caso raro, mas não pode gerar
    dias_taxa_nova negativo."""
    dist = regras.calcular_distribuicao_reajuste(
        Decimal("1000.00"), Decimal("110"), Decimal("100"), date(2026, 6, 10), date(2026, 6, 20)
    )
    assert len(dist.linhas) == 1
    linha = dist.linhas[0]
    assert linha.diferenca > 0


def test_percentual_de_variacao():
    percentual = regras.calcular_percentual_reajuste(Decimal("110"), Decimal("100"))
    assert percentual == Decimal("0.1")
