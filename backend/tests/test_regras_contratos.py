from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.contrato import Contrato, ExcecaoTetoVigencia, FormaContratacao, GarantiaContrato, StatusContrato
from app.models.instrumento_processual import (
    FundamentacaoLei,
    InstrumentoProcessual,
    TipoInstrumento,
)
from app.services import contratos as regras


def _contrato(**overrides) -> Contrato:
    padrao = dict(
        numero_contrato="CT-1",
        tipo_servico="Serviço X",
        objeto="Objeto do contrato",
        fornecedor_id="00000000-0000-0000-0000-000000000000",
        forma_contratacao=FormaContratacao.PREGAO_ELETRONICO,
        status=StatusContrato.VIGENTE,
        data_assinatura_original=date(2024, 1, 10),
        valor_inicial=Decimal("100000.00"),
        valor_pago=Decimal("0.00"),
        valor_pago_anterior_sistema=Decimal("0.00"),
        # Contrato() em memória (sem passar por flush no banco) não aplica o
        # default=True da coluna — sem isto aqui o valor fica None, e
        # `not None` também dá True, mascarando o teste do caso comum.
        faturamento_gerido_pela_gct=True,
    )
    padrao.update(overrides)
    contrato = Contrato(**padrao)
    contrato.instrumentos = []
    contrato.garantias = []
    contrato.processos = []
    return contrato


def _garantia(**overrides) -> GarantiaContrato:
    padrao = dict(
        registrado_por_id="00000000-0000-0000-0000-000000000000",
        registrado_em=datetime(2024, 1, 1),
    )
    padrao.update(overrides)
    return GarantiaContrato(**padrao)


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


def test_garantia_atual_usa_registro_mais_recente():
    contrato = _contrato()
    contrato.garantias = [
        _garantia(
            data_inicio_garantia=date(2024, 1, 1),
            data_fim_garantia=date(2025, 1, 1),
            registrado_em=datetime(2024, 1, 1),
        ),
        _garantia(
            data_inicio_garantia=date(2024, 1, 1),
            data_fim_garantia=date(2026, 1, 1),
            registrado_em=datetime(2024, 6, 1),
        ),
    ]
    inicio, fim = regras.garantia_atual(contrato)
    assert inicio == date(2024, 1, 1)
    assert fim == date(2026, 1, 1)


def test_garantia_atual_sem_registros_retorna_none():
    contrato = _contrato()
    assert regras.garantia_atual(contrato) == (None, None)


def test_calcular_alertas_garantia_usa_registro_mais_recente():
    contrato = _contrato()
    contrato.garantias = [_garantia(data_fim_garantia=date(2026, 2, 1), registrado_em=datetime(2024, 1, 1))]
    alertas = regras.calcular_alertas(contrato, hoje=date(2026, 1, 5))
    assert alertas.alerta_garantia == "1_meses"


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


# --------------------------------------------------------------------------
# Contador de datas: prazo em meses → fim da vigência
# --------------------------------------------------------------------------
def test_fim_de_vigencia_e_a_vespera_do_mesmo_dia():
    """13/06/2022 + 24 meses = 12/06/2024 — o dia de início conta como
    primeiro dia de vigência, então o prazo fecha na véspera."""
    assert regras.calcular_fim_vigencia(date(2022, 6, 13), 24) == date(2024, 6, 12)


def test_prazo_de_doze_meses():
    assert regras.calcular_fim_vigencia(date(2026, 1, 1), 12) == date(2026, 12, 31)


def test_mes_mais_curto_nao_vira_erro_de_dia():
    """31/01 + 1 mês cai no último dia de fevereiro, não estoura para março."""
    assert regras.calcular_fim_vigencia(date(2026, 1, 31), 1) == date(2026, 2, 27)


def test_ano_bissexto():
    assert regras.calcular_fim_vigencia(date(2024, 1, 31), 1) == date(2024, 2, 28)


def test_inicio_em_dia_29_de_fevereiro():
    assert regras.calcular_fim_vigencia(date(2024, 2, 29), 12) == date(2025, 2, 27)


# --------------------------------------------------------------------------
# Contagem regressiva
# --------------------------------------------------------------------------
def test_tempo_restante_decompoe_em_meses_e_dias():
    restante = regras.tempo_restante(date(2026, 6, 12), hoje=date(2026, 3, 1))
    assert restante is not None
    assert restante.vencido is False
    assert (restante.meses, restante.dias) == (3, 11)
    assert restante.dias_totais == 103


def test_tempo_restante_marca_vencido_e_conta_o_decorrido():
    restante = regras.tempo_restante(date(2026, 1, 10), hoje=date(2026, 3, 1))
    assert restante is not None
    assert restante.vencido is True
    assert (restante.meses, restante.dias) == (1, 19)


def test_tempo_restante_sem_vigencia_definida():
    assert regras.tempo_restante(None) is None


def test_teto_de_cinco_anos_barra_prazo_longo_no_cadastro():
    """A regra dos 5 anos continua valendo: um prazo em meses que a ultrapasse
    é recusado do mesmo jeito que uma data digitada à mão."""
    contrato = _contrato(data_assinatura_original=date(2026, 1, 10))
    fim = regras.calcular_fim_vigencia(date(2026, 1, 10), 72)
    with pytest.raises(regras.TetoVigenciaExcedido):
        regras.validar_teto_cinco_anos(contrato, fim)


# --------------------------------------------------------------------------
# Exceção ao teto de 5 anos (art. 71, I e II, da Lei 13.303/16)
# --------------------------------------------------------------------------
def test_excecao_ao_teto_remove_a_data_limite():
    """Locação de imóvel (inciso II) é o caso típico: prazo longo é prática
    rotineira de mercado, então a lei não impõe teto, não estende para outro
    número de anos."""
    contrato = _contrato(
        data_assinatura_original=date(2024, 1, 10),
        excecao_teto_vigencia=ExcecaoTetoVigencia.ART_71_II,
    )
    assert regras.teto_vigencia(contrato) is None


def test_excecao_ao_teto_libera_prazo_que_normalmente_seria_barrado():
    contrato = _contrato(
        data_assinatura_original=date(2024, 1, 10),
        excecao_teto_vigencia=ExcecaoTetoVigencia.ART_71_II,
    )
    regras.validar_teto_cinco_anos(contrato, date(2044, 1, 10))  # 20 anos — não deve levantar


def test_sem_excecao_o_teto_de_cinco_anos_continua_valendo():
    contrato = _contrato(data_assinatura_original=date(2024, 1, 10), excecao_teto_vigencia=None)
    assert regras.teto_vigencia(contrato) == date(2029, 1, 10)
    with pytest.raises(regras.TetoVigenciaExcedido):
        regras.validar_teto_cinco_anos(contrato, date(2029, 1, 11))
