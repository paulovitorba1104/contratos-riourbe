from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.contrato import ContratoAtualizar, ContratoCriar, InstrumentoOrigemCriar, ProcessoCriar

PROCESSO_BASE = dict(numero_processo="SEI-1", sistema_origem="sei_rio", tipo="principal")

DADOS_BASE = dict(
    numero_contrato="CT-1",
    tipo_servico="Serviço X",
    objeto="Objeto do contrato",
    fornecedor_id="00000000-0000-0000-0000-000000000000",
    forma_contratacao="pregao_eletronico",
    data_assinatura_original=date(2024, 1, 10),
    valor_inicial=Decimal("1000.00"),
    fiscais_ids=["00000000-0000-0000-0000-000000000000"],
    processos=[PROCESSO_BASE],
)

INSTRUMENTO_ORIGEM_BASE = dict(
    modelo_ripm_id="00000000-0000-0000-0000-000000000000",
    fundamentacao_lei="lei_13303_16",
    fundamentacao_artigo="art. 1",
    data_inicio_vigencia=date(2024, 1, 10),
    data_fim_vigencia=date(2026, 1, 10),
)


def test_instrumento_origem_aceita_datas_validas():
    instrumento = InstrumentoOrigemCriar(**INSTRUMENTO_ORIGEM_BASE)
    assert instrumento.data_fim_vigencia == date(2026, 1, 10)


def test_instrumento_origem_rejeita_fim_antes_do_inicio():
    with pytest.raises(ValidationError):
        InstrumentoOrigemCriar(**{**INSTRUMENTO_ORIGEM_BASE, "data_fim_vigencia": date(2023, 1, 1)})


def test_contrato_criar_exige_instrumento_origem():
    with pytest.raises(ValidationError):
        ContratoCriar(**DADOS_BASE)


def test_contrato_criar_aceita_com_instrumento_origem():
    contrato = ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE)
    assert contrato.instrumento_origem.data_inicio_vigencia == date(2024, 1, 10)


def test_contrato_criar_nao_exige_modelo_ripm_no_instrumento_origem():
    """RIPM é só um checklist de apoio administrativo — não é obrigatório
    para registrar a vigência inicial do contrato."""
    dados_sem_ripm = {k: v for k, v in INSTRUMENTO_ORIGEM_BASE.items() if k != "modelo_ripm_id"}
    contrato = ContratoCriar(**DADOS_BASE, instrumento_origem=dados_sem_ripm)
    assert contrato.instrumento_origem.modelo_ripm_id is None
    # As datas de vigência — o que de fato alimenta o teto de 5 anos — continuam exigidas.
    assert contrato.instrumento_origem.data_inicio_vigencia == date(2024, 1, 10)
    assert contrato.instrumento_origem.data_fim_vigencia == date(2026, 1, 10)


def test_processo_criar_aceita_sistema_e_tipo_validos():
    processo = ProcessoCriar(**PROCESSO_BASE)
    assert processo.sistema_origem == "sei_rio"
    assert processo.tipo == "principal"


def test_processo_criar_rejeita_sistema_invalido():
    with pytest.raises(ValidationError):
        ProcessoCriar(**{**PROCESSO_BASE, "sistema_origem": "sistema_inexistente"})


def test_contrato_criar_exige_ao_menos_um_processo():
    dados_sem_processos = {k: v for k, v in DADOS_BASE.items() if k != "processos"}
    with pytest.raises(ValidationError):
        ContratoCriar(**dados_sem_processos, instrumento_origem=INSTRUMENTO_ORIGEM_BASE, processos=[])


def test_contrato_criar_aceita_mais_de_um_processo_apenso():
    dados = {**DADOS_BASE, "processos": [PROCESSO_BASE, {"numero_processo": "SICOP-1", "sistema_origem": "sicop", "tipo": "apenso"}]}
    contrato = ContratoCriar(**dados, instrumento_origem=INSTRUMENTO_ORIGEM_BASE)
    assert len(contrato.processos) == 2
    assert contrato.processos[1].sistema_origem == "sicop"
    assert contrato.processos[1].tipo == "apenso"


def test_excecao_ao_teto_exige_justificativa_e_documento():
    """Marcar a exceção sem justificativa ou sem documento SEI é recusado —
    não pode virar uma exceção sem lastro nenhum."""
    with pytest.raises(ValidationError):
        ContratoCriar(
            **DADOS_BASE,
            instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
            excecao_teto_vigencia="art_71_ii",
        )
    with pytest.raises(ValidationError):
        ContratoCriar(
            **DADOS_BASE,
            instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
            excecao_teto_vigencia="art_71_ii",
            excecao_teto_justificativa="Locação de imóvel — prazo longo é prática de mercado.",
        )


def test_excecao_ao_teto_aceita_com_justificativa_e_documento():
    contrato = ContratoCriar(
        **DADOS_BASE,
        instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
        excecao_teto_vigencia="art_71_ii",
        excecao_teto_justificativa="Locação de imóvel — prazo longo é prática de mercado.",
        excecao_teto_documento_sei="SEI-12345",
    )
    assert contrato.excecao_teto_vigencia == "art_71_ii"


def test_contrato_atualizar_nao_exige_excecao_quando_nao_informada():
    """Edição comum (ex.: só objeto) não deve disparar a validação da exceção."""
    atualizacao = ContratoAtualizar(objeto="Objeto revisado")
    assert atualizacao.excecao_teto_vigencia is None


def test_contrato_atualizar_exige_lastro_ao_marcar_excecao():
    with pytest.raises(ValidationError):
        ContratoAtualizar(excecao_teto_vigencia="art_71_i")


def test_contrato_criar_exige_setor_quando_faturamento_nao_e_da_gct():
    with pytest.raises(ValidationError):
        ContratoCriar(
            **DADOS_BASE,
            instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
            faturamento_gerido_pela_gct=False,
        )


def test_contrato_criar_aceita_faturamento_de_outro_setor_com_setor_informado():
    contrato = ContratoCriar(
        **DADOS_BASE,
        instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
        faturamento_gerido_pela_gct=False,
        setor_responsavel_faturamento="RH",
    )
    assert contrato.setor_responsavel_faturamento == "RH"


def test_contrato_criar_faturamento_pela_gct_e_o_padrao():
    contrato = ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE)
    assert contrato.faturamento_gerido_pela_gct is True
    assert contrato.setor_responsavel_faturamento is None


def test_contrato_criar_valor_pago_anterior_sistema_padrao_e_zero():
    contrato = ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE)
    assert contrato.valor_pago_anterior_sistema == Decimal("0")


def test_contrato_atualizar_exige_setor_ao_marcar_faturamento_de_outro_setor():
    with pytest.raises(ValidationError):
        ContratoAtualizar(faturamento_gerido_pela_gct=False)


def test_contrato_atualizar_nao_exige_setor_quando_nao_mexe_no_faturamento():
    atualizacao = ContratoAtualizar(objeto="Objeto revisado")
    assert atualizacao.faturamento_gerido_pela_gct is None


def test_contrato_criar_aceita_modo_por_vigencia_sem_quantidade():
    """Modo padrão — a imensa maioria dos contratos não informa nada aqui."""
    contrato = ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE)
    assert contrato.modo_execucao == "por_vigencia"
    assert contrato.quantidade_execucoes_previstas is None


def test_contrato_criar_por_quantidade_exige_quantidade_prevista():
    with pytest.raises(ValidationError):
        ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE, modo_execucao="por_quantidade")


def test_contrato_criar_por_quantidade_aceita_com_quantidade_prevista():
    contrato = ContratoCriar(
        **DADOS_BASE,
        instrumento_origem=INSTRUMENTO_ORIGEM_BASE,
        modo_execucao="por_quantidade",
        quantidade_execucoes_previstas=3,
    )
    assert contrato.quantidade_execucoes_previstas == 3


def test_contrato_criar_por_vigencia_rejeita_quantidade_prevista():
    """Quantidade prevista só faz sentido junto com modo_execucao = por_quantidade."""
    with pytest.raises(ValidationError):
        ContratoCriar(**DADOS_BASE, instrumento_origem=INSTRUMENTO_ORIGEM_BASE, quantidade_execucoes_previstas=3)


def test_contrato_atualizar_por_quantidade_exige_quantidade_prevista():
    with pytest.raises(ValidationError):
        ContratoAtualizar(modo_execucao="por_quantidade")


def test_contrato_atualizar_nao_mexer_em_modo_execucao_nao_exige_nada():
    atualizacao = ContratoAtualizar(objeto="Objeto revisado")
    assert atualizacao.modo_execucao is None


def test_tempo_restante_do_servico_vira_schema():
    """O serviço devolve um dataclass e a ficha do contrato o serializa — sem
    `from_attributes` isso quebra o GET do contrato inteiro, não só o campo."""
    from datetime import date

    from app.schemas.contrato import TempoRestanteSaida
    from app.services.contratos import tempo_restante

    calculado = tempo_restante(date(2026, 6, 12), hoje=date(2026, 3, 1))
    saida = TempoRestanteSaida.model_validate(calculado)

    assert saida.vencido is False
    assert (saida.meses, saida.dias) == (3, 11)
