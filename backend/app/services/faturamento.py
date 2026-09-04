"""Regras de negócio do módulo de Faturamento.

O módulo é um **controle de faturas**: acompanha e registra o andamento da nota
dentro do processo, com conferência documental e tributária. A liquidação é ato
de outro setor, fora deste sistema, e por isso não existe no fluxo.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.contrato import Contrato, StatusContrato
from app.models.faturamento import (
    Fatura,
    MedicaoContrato,
    RegraTributaria,
    StatusFatura,
    StatusMedicao,
    TipoEventoFatura,
    Tributo,
)


class RegraFaturamentoError(Exception):
    """Erro de regra de negócio do faturamento — vira 422 na API."""


class SaldoContratoExcedido(RegraFaturamentoError):
    pass


class TransicaoInvalida(RegraFaturamentoError):
    pass


# Estados terminais: nada mais acontece com a fatura depois deles.
STATUS_TERMINAIS = {StatusFatura.PAGA, StatusFatura.DEVOLVIDA, StatusFatura.CANCELADA}

# Para onde cada evento leva a fatura, e de quais status ele pode partir.
# É esta tabela que garante que o status nunca seja editado à mão: toda
# mudança nasce de um evento registrado com responsável e data.
TRANSICOES: dict[TipoEventoFatura, tuple[set[StatusFatura], StatusFatura]] = {
    # A conferência pode ser refeita quantas vezes for preciso enquanto a
    # fatura não for atestada — é assim que se resolve um item que voltou não
    # conforme: corrige a pendência e confere de novo.
    TipoEventoFatura.CONFERENCIA: (
        {StatusFatura.RECEBIDA, StatusFatura.EM_CONFERENCIA, StatusFatura.CONFERIDA},
        StatusFatura.CONFERIDA,
    ),
    TipoEventoFatura.ATESTO: ({StatusFatura.CONFERIDA}, StatusFatura.ATESTADA),
    TipoEventoFatura.PAGAMENTO: ({StatusFatura.ATESTADA}, StatusFatura.PAGA),
    TipoEventoFatura.DEVOLUCAO: (
        {
            StatusFatura.RECEBIDA,
            StatusFatura.EM_CONFERENCIA,
            StatusFatura.CONFERIDA,
            StatusFatura.ATESTADA,
        },
        StatusFatura.DEVOLVIDA,
    ),
    TipoEventoFatura.CANCELAMENTO: (
        {
            StatusFatura.RECEBIDA,
            StatusFatura.EM_CONFERENCIA,
            StatusFatura.CONFERIDA,
            StatusFatura.ATESTADA,
        },
        StatusFatura.CANCELADA,
    ),
}

ROTULOS_STATUS = {
    StatusFatura.RECEBIDA: "Recebida",
    StatusFatura.EM_CONFERENCIA: "Em conferência",
    StatusFatura.CONFERIDA: "Conferida",
    StatusFatura.ATESTADA: "Atestada",
    StatusFatura.PAGA: "Paga",
    StatusFatura.DEVOLVIDA: "Devolvida",
    StatusFatura.CANCELADA: "Cancelada",
}


def _dec(valor) -> Decimal:
    return Decimal(str(valor or 0))


def total_glosas(fatura: Fatura) -> Decimal:
    return sum((_dec(g.valor) for g in fatura.glosas), Decimal("0"))


def total_retencoes(fatura: Fatura) -> Decimal:
    """Soma o que efetivamente veio retido na nota — é o valor informado, não o
    esperado: o líquido reflete a nota real, e a divergência com o esperado é
    tratada como apontamento da conferência."""
    return sum((_dec(r.valor_informado) for r in fatura.retencoes), Decimal("0"))


def valor_liquido(fatura: Fatura) -> Decimal:
    """O que o fornecedor recebe: bruto menos glosas e menos retenções."""
    return _dec(fatura.valor_bruto) - total_glosas(fatura) - total_retencoes(fatura)


def valor_executado(fatura: Fatura) -> Decimal:
    """Quanto esta fatura consome do contrato.

    Retenção tributária não reduz execução contratual — é tributo retido na
    fonte, mas o contrato foi executado naquele valor. Glosa, sim, reduz: o
    serviço não foi prestado.
    """
    return _dec(fatura.valor_bruto) - total_glosas(fatura)


def faturas_consomem_contrato(faturas: list[Fatura]) -> Decimal:
    """Total já comprometido do contrato. Fatura cancelada ou devolvida não
    conta — a devolvida volta ao fornecedor e é reapresentada como outra nota."""
    return sum(
        (valor_executado(f) for f in faturas if f.status not in {StatusFatura.CANCELADA, StatusFatura.DEVOLVIDA}),
        Decimal("0"),
    )


def total_pago(faturas: list[Fatura]) -> Decimal:
    """Quanto já foi efetivamente pago — é o que alimenta o valor pago do
    contrato, aposentando o lançamento manual."""
    return sum((valor_executado(f) for f in faturas if f.status == StatusFatura.PAGA), Decimal("0"))


def validar_contrato_aceita_fatura(contrato: Contrato) -> None:
    if contrato.status == StatusContrato.ENCERRADO:
        raise RegraFaturamentoError(
            "Contrato encerrado não aceita novas faturas."
        )


def validar_saldo_disponivel(
    contrato: Contrato,
    faturas_existentes: list[Fatura],
    valor_bruto_nova: Decimal,
    valor_atualizado_contrato: Decimal,
) -> None:
    """Impede que a soma das faturas ultrapasse o valor atualizado do contrato
    (com aditivos já contabilizados)."""
    comprometido = faturas_consomem_contrato(faturas_existentes)
    saldo = _dec(valor_atualizado_contrato) - comprometido
    if _dec(valor_bruto_nova) > saldo:
        raise SaldoContratoExcedido(
            f"Valor da fatura (R$ {_dec(valor_bruto_nova):.2f}) ultrapassa o saldo disponível "
            f"do contrato (R$ {saldo:.2f})."
        )


def validar_medicao(contrato: Contrato, medicao: MedicaoContrato | None, medicao_ja_usada: bool) -> None:
    """Em contrato que exige medição, a fatura só entra vinculada a uma medição
    aprovada e ainda não usada por outra nota."""
    if not contrato.exige_medicao:
        return
    if medicao is None:
        raise RegraFaturamentoError(
            "Este contrato exige medição: informe a medição aprovada que originou a nota."
        )
    if medicao.status != StatusMedicao.APROVADA:
        raise RegraFaturamentoError("A medição informada ainda não foi aprovada.")
    if medicao_ja_usada:
        raise RegraFaturamentoError("Esta medição já foi usada por outra fatura.")


def validar_transicao(fatura: Fatura, evento: TipoEventoFatura) -> StatusFatura:
    """Devolve o status resultante do evento, recusando o que não faz sentido
    no fluxo (ex.: atestar uma fatura que ainda não foi conferida)."""
    if fatura.status in STATUS_TERMINAIS:
        raise TransicaoInvalida(
            f"Fatura {ROTULOS_STATUS[fatura.status].lower()} não aceita novos eventos."
        )
    origens, destino = TRANSICOES[evento]
    if fatura.status not in origens:
        permitidos = ", ".join(sorted(ROTULOS_STATUS[s].lower() for s in origens))
        raise TransicaoInvalida(
            f"Fatura {ROTULOS_STATUS[fatura.status].lower()} não pode receber esse evento "
            f"(esperado: {permitidos})."
        )
    return destino


def validar_conferencia_permite_atesto(fatura: Fatura) -> None:
    """Item obrigatório não conforme trava o avanço — a regra que impede o
    'passou batido'. Vale a conferência mais recente da fatura."""
    if not fatura.conferencias:
        raise RegraFaturamentoError("Registre a conferência documental antes de atestar a fatura.")

    ultima = max(fatura.conferencias, key=lambda c: c.conferido_em)
    pendentes = [
        item.descricao
        for item in ultima.itens
        if item.obrigatorio and item.situacao.value == "nao_conforme"
    ]
    if pendentes:
        raise RegraFaturamentoError(
            "Há item obrigatório não conforme na conferência: " + "; ".join(pendentes)
        )


def validar_divergencias_justificadas(fatura: Fatura) -> None:
    """Divergência tributária não trava o fluxo, mas avançar com ela exige
    justificativa registrada — fica gravado quem aceitou e por quê."""
    sem_justificativa = [
        r.tributo.value.upper()
        for r in fatura.retencoes
        if _dec(r.valor_esperado) != _dec(r.valor_informado) and not (r.observacao or "").strip()
    ]
    if sem_justificativa:
        raise RegraFaturamentoError(
            "Divergência tributária sem justificativa em: " + ", ".join(sem_justificativa)
        )


def regra_vigente(regras: list[RegraTributaria], tributo: Tributo, referencia: date) -> RegraTributaria | None:
    """A regra que valia na data de referência da nota — nota antiga é conferida
    pela legislação da época dela, não pela de hoje."""
    candidatas = [
        r
        for r in regras
        if r.tributo == tributo
        and r.ativo
        and r.vigencia_inicio <= referencia
        and (r.vigencia_fim is None or r.vigencia_fim >= referencia)
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda r: r.vigencia_inicio)


@dataclass
class RetencaoCalculada:
    tributo: Tributo
    base_calculo: Decimal
    aliquota: Decimal
    valor_esperado: Decimal


def calcular_retencao(regra: RegraTributaria, valor_bruto: Decimal) -> RetencaoCalculada:
    """Aplica o parâmetro cadastrado. O sistema não interpreta a legislação:
    alíquota, base e fundamentação vêm do cadastro de regras tributárias."""
    base = (_dec(valor_bruto) * _dec(regra.percentual_base) / Decimal("100")).quantize(Decimal("0.01"))
    esperado = (base * _dec(regra.aliquota) / Decimal("100")).quantize(Decimal("0.01"))
    return RetencaoCalculada(
        tributo=regra.tributo,
        base_calculo=base,
        aliquota=_dec(regra.aliquota),
        valor_esperado=esperado,
    )


def tem_divergencia(valor_esperado, valor_informado) -> bool:
    return _dec(valor_esperado) != _dec(valor_informado)


@dataclass
class AlertasFatura:
    alerta_vencimento: str | None
    divergencia_tributaria: bool


def calcular_alertas(fatura: Fatura, hoje: date | None = None) -> AlertasFatura:
    """Mesma filosofia dos relógios do Contratos: avisar antes de virar
    problema. Fatura já paga ou fora do fluxo não alerta vencimento."""
    hoje = hoje or date.today()

    alerta_vencimento: str | None = None
    if fatura.data_vencimento and fatura.status not in STATUS_TERMINAIS:
        dias = (fatura.data_vencimento - hoje).days
        if dias < 0:
            alerta_vencimento = "vencido"
        elif dias <= 7:
            alerta_vencimento = "1_semana"
        elif dias <= 30:
            alerta_vencimento = "1_mes"

    divergencia = any(
        tem_divergencia(r.valor_esperado, r.valor_informado) and not (r.observacao or "").strip()
        for r in fatura.retencoes
    )

    return AlertasFatura(alerta_vencimento=alerta_vencimento, divergencia_tributaria=divergencia)
