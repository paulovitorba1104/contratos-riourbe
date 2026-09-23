"""Calculadora de reajuste/apostilamento — seção 4.6 do plano.

Substitui a calculadora do cidadão (Banco Central) para a parte de conta:
dado o valor mensal antigo e a variação do índice entre dois meses-base
(a mesma fórmula que a cláusula de reajuste já traz — R = Po×[(I-Io)/Io]),
devolve o valor mensal reajustado e a distribuição mês a mês da diferença
retroativa a formalizar por apostilamento (o "Valor do Apostilamento" da
planilha de controle). O índice em si (IPCA-E, IGPM etc.) pode ser digitado
à mão ou, para o IPCA-E, buscado sozinho no SGS do Banco Central (ver
`app/core/bcb_sgs.py` e `GET /contratos/consultar-indice-ipca-e`) — outros
índices continuam informados por quem calcula.

Convenção de mês comercial de 30 dias para o pro-rata do primeiro mês
(quando o marco do reajuste cai no meio do mês) e do último (quando o
período coberto termina no meio do mês, tipicamente por fim de vigência) —
a mesma prática usada em cálculo de aluguel e reajuste no serviço público,
validada linha a linha contra uma planilha real de apostilamento.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta

DIAS_MES_COMERCIAL = 30
DUAS_CASAS = Decimal("0.01")


class PeriodoReajusteInvalido(Exception):
    """data_fim não é posterior a data_inicio, ou índice base é zero."""


def _dec(valor) -> Decimal:
    return Decimal(str(valor))


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)


def calcular_valor_mensal_reajustado(valor_mensal_antigo, indice_atual, indice_base) -> Decimal:
    """Po × (I/Io) — equivalente a Po + R, sendo R = Po×[(I-Io)/Io] a fórmula
    que a cláusula de reajuste traz (o valor do reajuste é só a parcela a
    somar; o valor mensal novo é o preço já com essa parcela dentro)."""
    io = _dec(indice_base)
    if io == 0:
        raise PeriodoReajusteInvalido("O índice base não pode ser zero.")
    return _arredondar(_dec(valor_mensal_antigo) * _dec(indice_atual) / io)


def calcular_percentual_reajuste(indice_atual, indice_base) -> Decimal:
    """(I-Io)/Io — o percentual de variação isolado, só para exibição."""
    io = _dec(indice_base)
    if io == 0:
        raise PeriodoReajusteInvalido("O índice base não pode ser zero.")
    return (_dec(indice_atual) - io) / io


@dataclass
class LinhaReajusteMensal:
    """Uma competência (mês) da distribuição do apostilamento."""

    competencia: date  # primeiro dia do mês
    valor_antigo: Decimal
    valor_reajustado: Decimal
    diferenca: Decimal


@dataclass
class DistribuicaoReajuste:
    valor_mensal_antigo: Decimal
    valor_mensal_novo: Decimal
    percentual_variacao: Decimal
    linhas: list[LinhaReajusteMensal]
    valor_total_apostilamento: Decimal  # soma das diferenças mensais
    valor_total_antigo: Decimal  # soma da coluna "valor antigo" — linha TOTAL do relatório
    valor_total_reajustado: Decimal  # soma da coluna "valor reajustado" — linha TOTAL do relatório


def calcular_distribuicao_reajuste(
    valor_mensal_antigo,
    indice_atual,
    indice_base,
    data_inicio: date,
    data_fim: date,
) -> DistribuicaoReajuste:
    """Mês a mês entre `data_inicio` (marco do reajuste, ex.: aniversário da
    vigência) e `data_fim` (o próximo marco ou o fim da vigência do
    contrato, o que vier primeiro — ambos inclusive), no molde exato da
    planilha "Distribuição do Apostilamento":

    - Mês do marco (`data_inicio`): dias antes do marco ainda à taxa antiga,
      dias a partir do marco (inclusive) já à taxa nova — um único mês pode
      misturar as duas.
    - Meses do meio: mês inteiro (30 dias) à taxa nova.
    - Mês final, só quando `data_fim` não cai no último dia do mês
      comercial (ou seja, quando o período termina no meio do mês, tipicamente
      porque a vigência do contrato termina ali): pro-rata até `data_fim.day`.
    - `valor_antigo`, em cada linha, é sempre a referência do mês inteiro
      (dia 1 até o fim considerado no mês) à taxa antiga — é o que já vinha
      sendo faturado antes de alguém processar o reajuste; a diferença
      mensal (reajustado − antigo) é o que o apostilamento formaliza.
    """
    if data_fim <= data_inicio:
        raise PeriodoReajusteInvalido("A data final deve ser posterior à data inicial do reajuste.")

    valor_mensal_novo = calcular_valor_mensal_reajustado(valor_mensal_antigo, indice_atual, indice_base)
    percentual = calcular_percentual_reajuste(indice_atual, indice_base)

    taxa_diaria_antiga = _dec(valor_mensal_antigo) / DIAS_MES_COMERCIAL
    taxa_diaria_nova = valor_mensal_novo / DIAS_MES_COMERCIAL

    linhas: list[LinhaReajusteMensal] = []
    competencia = date(data_inicio.year, data_inicio.month, 1)
    ultima_competencia = date(data_fim.year, data_fim.month, 1)

    while competencia <= ultima_competencia:
        eh_primeira = (competencia.year, competencia.month) == (data_inicio.year, data_inicio.month)
        eh_ultima = (competencia.year, competencia.month) == (data_fim.year, data_fim.month)

        dia_fim_mes = data_fim.day if eh_ultima else DIAS_MES_COMERCIAL
        valor_antigo_mes = _arredondar(dia_fim_mes * taxa_diaria_antiga)

        if eh_primeira:
            marco_dia = data_inicio.day
            dias_taxa_antiga = marco_dia - 1
            dias_taxa_nova = dia_fim_mes - marco_dia + 1
            valor_reajustado_mes = _arredondar(
                dias_taxa_antiga * taxa_diaria_antiga + dias_taxa_nova * taxa_diaria_nova
            )
        else:
            valor_reajustado_mes = _arredondar(dia_fim_mes * taxa_diaria_nova)

        linhas.append(
            LinhaReajusteMensal(
                competencia=competencia,
                valor_antigo=valor_antigo_mes,
                valor_reajustado=valor_reajustado_mes,
                diferenca=valor_reajustado_mes - valor_antigo_mes,
            )
        )
        competencia = competencia + relativedelta(months=1)

    valor_total = sum((linha.diferenca for linha in linhas), Decimal("0"))
    valor_total_antigo = sum((linha.valor_antigo for linha in linhas), Decimal("0"))
    valor_total_reajustado = sum((linha.valor_reajustado for linha in linhas), Decimal("0"))

    return DistribuicaoReajuste(
        valor_mensal_antigo=_arredondar(_dec(valor_mensal_antigo)),
        valor_mensal_novo=valor_mensal_novo,
        percentual_variacao=percentual,
        linhas=linhas,
        valor_total_apostilamento=valor_total,
        valor_total_antigo=valor_total_antigo,
        valor_total_reajustado=valor_total_reajustado,
    )
