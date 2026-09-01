from datetime import date
from decimal import Decimal

import pytest

from app.models.contrato import Contrato, FormaContratacao, StatusContrato
from app.models.instrumento_processual import (
    FundamentacaoLei,
    InstrumentoProcessual,
    TipoInstrumento,
)
from app.services import contratos as regras


def _contrato(**overrides) -> Contrato:
    padrao = dict(
        processo_sei="SEI-1",
        tipo_servico="Serviço X",
        objeto="Objeto do contrato",
        fornecedor_id="00000000-0000-0000-0000-000000000000",
        forma_contratacao=FormaContratacao.PREGAO_ELETRONICO,
        status=StatusContrato.VIGENTE,
        data_assinatura_original=date(2024, 1, 10),
        valor_inicial=Decimal("100000.00"),
        valor_pago=Decimal("0.00"),
    )
    padrao.update(overrides)
    contrato = Contrato(**padrao)
    contrato.instrumentos = []
    return contrato


def _instrumento(tipo: TipoInstrumento, **overrides) -> InstrumentoProcessual:
    padrao = dict(
        tipo=tipo,
        modelo_ripm_id="00000000-0000-0000-0000-000000000000",
        fundamentacao_lei=FundamentacaoLei.LEI_13303_16,
        fundamentacao_artigo="art. 1",
    )
    padrao.update(overrides)
    return InstrumentoProcessual(**padrao)


def test_valor_atualizado_soma_acrescimos_e_supressoes():
    contrato = _contrato(valor_inicial=Decimal("100000.00"))
    contrato.instrumentos = [
        _instrumento(TipoInstrumento.ACRESCIMO_VALOR, valor_delta=Decimal("10000.00")),
        _instrumento(TipoInstrumento.SUPRESSAO_VALOR, valor_delta=Decimal("-5000.00")),
    ]
    assert regras.calcular_valor_atualizado(contrato) == Decimal("105000.00")


def test_saldo_a_pagar_desconta_valor_pago():
    contrato = _contrato(valor_inicial=Decimal("100000.00"), valor_pago=Decimal("40000.00"))
    assert regras.calcular_saldo_a_pagar(contrato) == Decimal("60000.00")


def test_vigencia_atual_usa_instrumento_mais_recente():
    contrato = _contrato()
    contrato.instrumentos = [
        _instrumento(
            TipoInstrumento.ORIGEM, data_inicio_vigencia=date(2024, 1, 10), data_fim_vigencia=date(2025, 1, 10)
        ),
        _instrumento(
            TipoInstrumento.PRORROGACAO,
            data_inicio_vigencia=date(2025, 1, 10),
            data_fim_vigencia=date(2026, 1, 10),
        ),
    ]
    inicio, fim = regras.vigencia_atual(contrato)
    assert inicio == date(2025, 1, 10)
    assert fim == date(2026, 1, 10)


def test_vigencia_atual_sem_instrumentos_retorna_none():
    contrato = _contrato()
    assert regras.vigencia_atual(contrato) == (None, None)


def test_teto_vigencia_e_cinco_anos_apos_assinatura():
    contrato = _contrato(data_assinatura_original=date(2024, 1, 10))
    assert regras.teto_vigencia(contrato) == date(2029, 1, 10)


def test_validar_teto_cinco_anos_bloqueia_quando_ultrapassa():
    contrato = _contrato(data_assinatura_original=date(2024, 1, 10))
    with pytest.raises(regras.TetoVigenciaExcedido):
        regras.validar_teto_cinco_anos(contrato, date(2029, 1, 11))


def test_validar_teto_cinco_anos_aceita_no_limite():
    contrato = _contrato(data_assinatura_original=date(2024, 1, 10))
    regras.validar_teto_cinco_anos(contrato, date(2029, 1, 10))  # não deve levantar


@pytest.mark.parametrize(
    "data_fim,hoje,esperado",
    [
        (date(2026, 12, 1), date(2026, 1, 1), None),
        (date(2026, 7, 1), date(2026, 1, 5), "6_meses"),
        (date(2026, 4, 1), date(2026, 1, 5), "3_meses"),
        (date(2026, 2, 1), date(2026, 1, 5), "1_meses"),
        (date(2026, 1, 1), date(2026, 2, 1), "vencido"),
    ],
)
def test_calcular_alertas_vigencia(data_fim, hoje, esperado):
    contrato = _contrato()
    contrato.instrumentos = [
        _instrumento(
            TipoInstrumento.ORIGEM,
            data_inicio_vigencia=date(2024, 1, 1),
            data_fim_vigencia=data_fim,
        )
    ]
    alertas = regras.calcular_alertas(contrato, hoje=hoje)
    assert alertas.alerta_vigencia == esperado


def test_aplicar_efeitos_status_suspensao():
    contrato = _contrato()
    regras.aplicar_efeitos_status(contrato, TipoInstrumento.SUSPENSAO)
    assert contrato.status == StatusContrato.SUSPENSO


def test_aplicar_efeitos_status_rescisao_encerra():
    contrato = _contrato()
    regras.aplicar_efeitos_status(contrato, TipoInstrumento.RESCISAO_EXTINCAO)
    assert contrato.status == StatusContrato.ENCERRADO


def test_aplicar_efeitos_status_tipo_neutro_nao_muda_status():
    contrato = _contrato()
    regras.aplicar_efeitos_status(contrato, TipoInstrumento.APOSTILAMENTO)
    assert contrato.status == StatusContrato.VIGENTE


def test_aplicar_efeitos_status_bloqueia_contrato_encerrado():
    contrato = _contrato(status=StatusContrato.ENCERRADO)
    with pytest.raises(regras.ContratoEncerradoError):
        regras.aplicar_efeitos_status(contrato, TipoInstrumento.APOSTILAMENTO)
