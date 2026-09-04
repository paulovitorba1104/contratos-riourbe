from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.contrato import Contrato, FormaContratacao, StatusContrato
from app.models.faturamento import (
    ConferenciaFatura,
    Fatura,
    GlosaFatura,
    ItemConferencia,
    MedicaoContrato,
    RegraTributaria,
    RetencaoFatura,
    SituacaoItemConferencia,
    StatusFatura,
    StatusMedicao,
    TipoEventoFatura,
    Tributo,
)
from app.services import faturamento as regras

UUID_ZERO = "00000000-0000-0000-0000-000000000000"


def _contrato(**overrides) -> Contrato:
    padrao = dict(
        numero_contrato="CT-1",
        tipo_servico="Limpeza",
        objeto="Objeto do contrato",
        fornecedor_id=UUID_ZERO,
        forma_contratacao=FormaContratacao.PREGAO_ELETRONICO,
        status=StatusContrato.VIGENTE,
        data_assinatura_original=date(2026, 1, 10),
        valor_inicial=Decimal("100000.00"),
        valor_pago=Decimal("0.00"),
        exige_medicao=False,
    )
    padrao.update(overrides)
    contrato = Contrato(**padrao)
    contrato.instrumentos = []
    contrato.garantias = []
    contrato.processos = []
    return contrato


def _fatura(**overrides) -> Fatura:
    padrao = dict(
        contrato_id=UUID_ZERO,
        numero_nota_fiscal="95",
        competencia="2026-01",
        data_emissao=date(2026, 2, 10),
        data_recebimento=date(2026, 2, 10),
        valor_bruto=Decimal("17528.96"),
        status=StatusFatura.RECEBIDA,
    )
    padrao.update(overrides)
    fatura = Fatura(**padrao)
    fatura.glosas = []
    fatura.retencoes = []
    fatura.conferencias = []
    fatura.eventos = []
    return fatura


def _regra(**overrides) -> RegraTributaria:
    padrao = dict(
        tributo=Tributo.ISS,
        descricao="ISS sobre serviços",
        aliquota=Decimal("5"),
        percentual_base=Decimal("100"),
        vigencia_inicio=date(2026, 1, 1),
        vigencia_fim=None,
        ativo=True,
    )
    padrao.update(overrides)
    return RegraTributaria(**padrao)


# --------------------------------------------------------------------------
# Valores
# --------------------------------------------------------------------------
def test_valor_liquido_desconta_glosas_e_retencoes():
    fatura = _fatura(valor_bruto=Decimal("10000.00"))
    fatura.glosas = [GlosaFatura(valor=Decimal("500.00"), motivo="Serviço não prestado")]
    fatura.retencoes = [
        RetencaoFatura(
            tributo=Tributo.ISS,
            base_calculo=Decimal("10000.00"),
            aliquota=Decimal("5"),
            valor_esperado=Decimal("500.00"),
            valor_informado=Decimal("500.00"),
        )
    ]
    assert regras.valor_liquido(fatura) == Decimal("9000.00")


def test_valor_executado_desconta_glosa_mas_nao_retencao():
    """Retenção é tributo retido na fonte — o contrato foi executado naquele
    valor. Glosa, sim, reduz a execução."""
    fatura = _fatura(valor_bruto=Decimal("10000.00"))
    fatura.glosas = [GlosaFatura(valor=Decimal("500.00"), motivo="Item não entregue")]
    fatura.retencoes = [
        RetencaoFatura(
            tributo=Tributo.INSS,
            base_calculo=Decimal("10000.00"),
            aliquota=Decimal("11"),
            valor_esperado=Decimal("1100.00"),
            valor_informado=Decimal("1100.00"),
        )
    ]
    assert regras.valor_executado(fatura) == Decimal("9500.00")


def test_total_pago_considera_apenas_faturas_pagas():
    paga = _fatura(valor_bruto=Decimal("1000.00"), status=StatusFatura.PAGA)
    atestada = _fatura(valor_bruto=Decimal("2000.00"), status=StatusFatura.ATESTADA)
    assert regras.total_pago([paga, atestada]) == Decimal("1000.00")


def test_fatura_cancelada_ou_devolvida_nao_consome_contrato():
    ativa = _fatura(valor_bruto=Decimal("1000.00"))
    cancelada = _fatura(valor_bruto=Decimal("5000.00"), status=StatusFatura.CANCELADA)
    devolvida = _fatura(valor_bruto=Decimal("7000.00"), status=StatusFatura.DEVOLVIDA)
    assert regras.faturas_consomem_contrato([ativa, cancelada, devolvida]) == Decimal("1000.00")


# --------------------------------------------------------------------------
# Saldo do contrato
# --------------------------------------------------------------------------
def test_saldo_recusa_fatura_que_estoura_contrato():
    contrato = _contrato()
    existente = _fatura(valor_bruto=Decimal("90000.00"))
    with pytest.raises(regras.SaldoContratoExcedido):
        regras.validar_saldo_disponivel(
            contrato, [existente], Decimal("20000.00"), Decimal("100000.00")
        )


def test_saldo_aceita_fatura_dentro_do_limite():
    contrato = _contrato()
    existente = _fatura(valor_bruto=Decimal("90000.00"))
    regras.validar_saldo_disponivel(contrato, [existente], Decimal("10000.00"), Decimal("100000.00"))


def test_contrato_encerrado_nao_aceita_fatura():
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_contrato_aceita_fatura(_contrato(status=StatusContrato.ENCERRADO))


# --------------------------------------------------------------------------
# Medição
# --------------------------------------------------------------------------
def test_contrato_que_exige_medicao_recusa_fatura_sem_medicao():
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_medicao(_contrato(exige_medicao=True), None, medicao_ja_usada=False)


def test_medicao_nao_aprovada_e_recusada():
    medicao = MedicaoContrato(
        contrato_id=UUID_ZERO,
        numero_medicao="1",
        competencia="2026-01",
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=date(2026, 1, 31),
        valor_medido=Decimal("1000.00"),
        status=StatusMedicao.EM_ELABORACAO,
    )
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_medicao(_contrato(exige_medicao=True), medicao, medicao_ja_usada=False)


def test_medicao_ja_usada_por_outra_fatura_e_recusada():
    medicao = MedicaoContrato(
        contrato_id=UUID_ZERO,
        numero_medicao="1",
        competencia="2026-01",
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=date(2026, 1, 31),
        valor_medido=Decimal("1000.00"),
        status=StatusMedicao.APROVADA,
    )
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_medicao(_contrato(exige_medicao=True), medicao, medicao_ja_usada=True)


def test_contrato_sem_medicao_ignora_a_regra():
    regras.validar_medicao(_contrato(exige_medicao=False), None, medicao_ja_usada=False)


# --------------------------------------------------------------------------
# Fluxo de status
# --------------------------------------------------------------------------
def test_atesto_exige_fatura_conferida():
    with pytest.raises(regras.TransicaoInvalida):
        regras.validar_transicao(_fatura(status=StatusFatura.RECEBIDA), TipoEventoFatura.ATESTO)


def test_conferencia_leva_para_conferida():
    assert (
        regras.validar_transicao(_fatura(status=StatusFatura.RECEBIDA), TipoEventoFatura.CONFERENCIA)
        == StatusFatura.CONFERIDA
    )


def test_conferencia_pode_ser_refeita_enquanto_nao_atestada():
    """Refazer a conferência é o caminho normal quando um item obrigatório
    volta não conforme e depois é regularizado."""
    assert (
        regras.validar_transicao(
            _fatura(status=StatusFatura.CONFERIDA), TipoEventoFatura.CONFERENCIA
        )
        == StatusFatura.CONFERIDA
    )


def test_pagamento_so_apos_atesto():
    assert (
        regras.validar_transicao(_fatura(status=StatusFatura.ATESTADA), TipoEventoFatura.PAGAMENTO)
        == StatusFatura.PAGA
    )
    with pytest.raises(regras.TransicaoInvalida):
        regras.validar_transicao(_fatura(status=StatusFatura.CONFERIDA), TipoEventoFatura.PAGAMENTO)


def test_fatura_paga_nao_aceita_novos_eventos():
    with pytest.raises(regras.TransicaoInvalida):
        regras.validar_transicao(_fatura(status=StatusFatura.PAGA), TipoEventoFatura.DEVOLUCAO)


# --------------------------------------------------------------------------
# Conferência documental
# --------------------------------------------------------------------------
def _conferencia_com(situacao, obrigatorio=True) -> ConferenciaFatura:
    conferencia = ConferenciaFatura(fatura_id=UUID_ZERO, conferido_por_id=UUID_ZERO)
    conferencia.conferido_em = datetime(2026, 2, 10)
    conferencia.itens = [
        ItemConferencia(
            ordem=0, descricao="Certidão de FGTS", obrigatorio=obrigatorio, situacao=situacao
        )
    ]
    return conferencia


def test_item_obrigatorio_nao_conforme_trava_atesto():
    fatura = _fatura()
    fatura.conferencias = [_conferencia_com(SituacaoItemConferencia.NAO_CONFORME)]
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_conferencia_permite_atesto(fatura)


def test_item_nao_obrigatorio_nao_trava_atesto():
    fatura = _fatura()
    fatura.conferencias = [
        _conferencia_com(SituacaoItemConferencia.NAO_CONFORME, obrigatorio=False)
    ]
    regras.validar_conferencia_permite_atesto(fatura)


def test_atesto_exige_conferencia_registrada():
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_conferencia_permite_atesto(_fatura())


# --------------------------------------------------------------------------
# Conferência tributária
# --------------------------------------------------------------------------
def test_calculo_de_retencao_aplica_aliquota_da_regra():
    calculo = regras.calcular_retencao(_regra(aliquota=Decimal("5")), Decimal("10000.00"))
    assert calculo.base_calculo == Decimal("10000.00")
    assert calculo.valor_esperado == Decimal("500.00")


def test_calculo_respeita_base_reduzida():
    calculo = regras.calcular_retencao(
        _regra(aliquota=Decimal("11"), percentual_base=Decimal("50")), Decimal("10000.00")
    )
    assert calculo.base_calculo == Decimal("5000.00")
    assert calculo.valor_esperado == Decimal("550.00")


def test_regra_vigente_usa_a_que_valia_na_data_da_nota():
    antiga = _regra(aliquota=Decimal("3"), vigencia_inicio=date(2025, 1, 1), vigencia_fim=date(2025, 12, 31))
    nova = _regra(aliquota=Decimal("5"), vigencia_inicio=date(2026, 1, 1))
    escolhida = regras.regra_vigente([antiga, nova], Tributo.ISS, date(2025, 6, 1))
    assert escolhida is antiga


def test_regra_inativa_e_ignorada():
    assert regras.regra_vigente([_regra(ativo=False)], Tributo.ISS, date(2026, 6, 1)) is None


def test_divergencia_sem_justificativa_trava_avanco():
    fatura = _fatura()
    fatura.retencoes = [
        RetencaoFatura(
            tributo=Tributo.ISS,
            base_calculo=Decimal("10000.00"),
            aliquota=Decimal("5"),
            valor_esperado=Decimal("500.00"),
            valor_informado=Decimal("300.00"),
        )
    ]
    with pytest.raises(regras.RegraFaturamentoError):
        regras.validar_divergencias_justificadas(fatura)


def test_divergencia_justificada_libera_avanco():
    fatura = _fatura()
    fatura.retencoes = [
        RetencaoFatura(
            tributo=Tributo.ISS,
            base_calculo=Decimal("10000.00"),
            aliquota=Decimal("5"),
            valor_esperado=Decimal("500.00"),
            valor_informado=Decimal("300.00"),
            observacao="Retenção parcial acordada com o fornecedor.",
        )
    ]
    regras.validar_divergencias_justificadas(fatura)


# --------------------------------------------------------------------------
# Alertas
# --------------------------------------------------------------------------
def test_alerta_de_vencimento_marca_fatura_vencida():
    fatura = _fatura(data_vencimento=date(2026, 3, 1))
    alertas = regras.calcular_alertas(fatura, hoje=date(2026, 3, 10))
    assert alertas.alerta_vencimento == "vencido"


def test_fatura_paga_nao_alerta_vencimento():
    fatura = _fatura(data_vencimento=date(2026, 3, 1), status=StatusFatura.PAGA)
    alertas = regras.calcular_alertas(fatura, hoje=date(2026, 3, 10))
    assert alertas.alerta_vencimento is None


def test_divergencia_tributaria_aparece_nos_alertas():
    fatura = _fatura()
    fatura.retencoes = [
        RetencaoFatura(
            tributo=Tributo.IRRF,
            base_calculo=Decimal("10000.00"),
            aliquota=Decimal("1.5"),
            valor_esperado=Decimal("150.00"),
            valor_informado=Decimal("100.00"),
        )
    ]
    assert regras.calcular_alertas(fatura, hoje=date(2026, 2, 11)).divergencia_tributaria is True
