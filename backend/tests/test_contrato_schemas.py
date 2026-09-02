from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.contrato import ContratoCriar, InstrumentoOrigemCriar, ProcessoCriar

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
