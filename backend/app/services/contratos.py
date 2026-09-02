"""Regras de negócio do Módulo Contratos — seção 4 do plano de desenvolvimento.

Mantido como funções puras sobre os modelos (sem consultas ao banco aqui
dentro) para ficar fácil de testar isoladamente.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from app.models.contrato import Contrato, StatusContrato
from app.models.instrumento_processual import (
    TIPOS_QUE_DEFINEM_VIGENCIA,
    InstrumentoProcessual,
    TipoInstrumento,
)

TIPOS_DE_VALOR = {TipoInstrumento.ACRESCIMO_VALOR, TipoInstrumento.SUPRESSAO_VALOR}

LIMITES_ALERTA_VIGENCIA_MESES = (1, 3, 6)
LIMITES_ALERTA_GARANTIA_MESES = (1, 3)


class TetoVigenciaExcedido(Exception):
    """Prorrogação levaria o contrato a ultrapassar o teto de 5 anos (Lei 13.303/16)."""


class ContratoEncerradoError(Exception):
    """Contrato encerrado/extinto é terminal — não aceita novos instrumentos."""


def calcular_valor_atualizado(contrato: Contrato) -> Decimal:
    total = Decimal(str(contrato.valor_inicial))
    for instrumento in contrato.instrumentos:
        if instrumento.tipo in TIPOS_DE_VALOR and instrumento.valor_delta is not None:
            total += Decimal(str(instrumento.valor_delta))
    return total


def calcular_saldo_a_pagar(contrato: Contrato) -> Decimal:
    return calcular_valor_atualizado(contrato) - Decimal(str(contrato.valor_pago))


def garantia_atual(contrato: Contrato) -> tuple[date | None, date | None]:
    """Relógio 3: garantia contratual vigente — a mais recentemente registrada
    no histórico (nunca a de maior data, já que uma correção pode inserir uma
    data anterior à do registro que ela corrige)."""
    if not contrato.garantias:
        return None, None
    mais_recente = max(contrato.garantias, key=lambda g: g.registrado_em)
    return mais_recente.data_inicio_garantia, mais_recente.data_fim_garantia


def vigencia_atual(contrato: Contrato) -> tuple[date | None, date | None]:
    """Relógio 1: período de vigência ativo — o mais recente entre origem e prorrogações."""
    candidatos = [
        i
        for i in contrato.instrumentos
        if i.tipo in TIPOS_QUE_DEFINEM_VIGENCIA and i.data_fim_vigencia is not None
    ]
    if not candidatos:
        return None, None
    mais_recente = max(candidatos, key=lambda i: i.data_fim_vigencia)
    return mais_recente.data_inicio_vigencia, mais_recente.data_fim_vigencia


def teto_vigencia(contrato: Contrato) -> date:
    """Relógio 2: data-limite absoluta — 5 anos desde a assinatura original."""
    return contrato.data_assinatura_original + relativedelta(years=5)


def validar_teto_cinco_anos(contrato: Contrato, nova_data_fim_vigencia: date) -> None:
    limite = teto_vigencia(contrato)
    if nova_data_fim_vigencia > limite:
        raise TetoVigenciaExcedido(
            f"Esta prorrogação levaria a vigência até {nova_data_fim_vigencia.isoformat()}, "
            f"ultrapassando o teto de 5 anos da Lei 13.303/16 (limite: {limite.isoformat()})."
        )


def _nivel_alerta(data_limite: date | None, hoje: date, limites_meses: tuple[int, ...]) -> str | None:
    if data_limite is None:
        return None
    if hoje > data_limite:
        return "vencido"
    for meses in sorted(limites_meses):
        inicio_janela = data_limite - relativedelta(months=meses)
        if hoje >= inicio_janela:
            return f"{meses}_meses"
    return None


@dataclass
class AlertasContrato:
    vigencia_fim: date | None
    alerta_vigencia: str | None
    garantia_fim: date | None
    alerta_garantia: str | None


def calcular_alertas(contrato: Contrato, hoje: date | None = None) -> AlertasContrato:
    hoje = hoje or date.today()
    _, vigencia_fim = vigencia_atual(contrato)
    _, garantia_fim = garantia_atual(contrato)
    return AlertasContrato(
        vigencia_fim=vigencia_fim,
        alerta_vigencia=_nivel_alerta(vigencia_fim, hoje, LIMITES_ALERTA_VIGENCIA_MESES),
        garantia_fim=garantia_fim,
        alerta_garantia=_nivel_alerta(garantia_fim, hoje, LIMITES_ALERTA_GARANTIA_MESES),
    )


def aplicar_efeitos_status(contrato: Contrato, tipo_instrumento: TipoInstrumento) -> None:
    """Só suspensão e extinção mudam o status macro (seção 4.3) — chamar
    antes de persistir um novo InstrumentoProcessual."""
    if contrato.status == StatusContrato.ENCERRADO:
        raise ContratoEncerradoError(
            "Este contrato está encerrado/extinto (status terminal) — não é possível registrar novos "
            "instrumentos processuais."
        )
    if tipo_instrumento == TipoInstrumento.SUSPENSAO:
        contrato.status = StatusContrato.SUSPENSO
    elif tipo_instrumento == TipoInstrumento.RESCISAO_EXTINCAO:
        contrato.status = StatusContrato.ENCERRADO


def validar_instrumento(contrato: Contrato, instrumento: InstrumentoProcessual) -> None:
    """Validações que dependem do contrato pai — teto de 5 anos e status terminal.
    Validações de formato por tipo (quais campos cada tipo exige) ficam no schema Pydantic."""
    if instrumento.tipo in TIPOS_QUE_DEFINEM_VIGENCIA and instrumento.data_fim_vigencia is not None:
        validar_teto_cinco_anos(contrato, instrumento.data_fim_vigencia)
