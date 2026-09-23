from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.instrumento import InstrumentoProcessualCriar

DADOS_ORIGEM = dict(
    tipo="origem",
    fundamentacao="Lei 13.303/16, art. 1",
    data_inicio_vigencia=date(2024, 1, 10),
    data_fim_vigencia=date(2026, 1, 10),
)


def test_instrumento_origem_nao_exige_modelo_ripm():
    """RIPM é só um checklist de apoio administrativo, não documento jurídico
    do processo — não pode ser obrigatório para registrar o instrumento."""
    instrumento = InstrumentoProcessualCriar(**DADOS_ORIGEM)
    assert instrumento.modelo_ripm_id is None


def test_instrumento_origem_aceita_modelo_ripm_quando_informado():
    instrumento = InstrumentoProcessualCriar(
        **DADOS_ORIGEM, modelo_ripm_id="00000000-0000-0000-0000-000000000000"
    )
    assert instrumento.modelo_ripm_id is not None


def test_instrumento_origem_ainda_exige_fundamentacao_legal():
    dados_sem_fundamentacao = {k: v for k, v in DADOS_ORIGEM.items() if k != "fundamentacao"}
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**dados_sem_fundamentacao)


def test_instrumento_origem_ainda_exige_datas_de_vigencia():
    dados_sem_datas = {k: v for k, v in DADOS_ORIGEM.items() if k != "data_fim_vigencia"}
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**dados_sem_datas)


DADOS_APOSTILAMENTO_BASE = dict(
    tipo="apostilamento",
    fundamentacao="Lei 13.303/16, art. 71",
)

DADOS_REAJUSTE = dict(
    reajuste_indice_nome="IPCA-E",
    reajuste_indice_atual="7169.264543",
    reajuste_indice_base="6500.00",
    reajuste_valor_mensal_antigo="118470.50",
    reajuste_data_inicio=date(2026, 6, 14),
    reajuste_data_fim=date(2027, 6, 13),
)


def test_apostilamento_comum_aceita_valor_delta_livre_sem_reajuste():
    instrumento = InstrumentoProcessualCriar(**DADOS_APOSTILAMENTO_BASE, valor_delta="1000.00")
    assert instrumento.valor_delta == 1000
    assert instrumento.reajuste_data_inicio is None


def test_apostilamento_de_reajuste_aceita_os_6_campos():
    instrumento = InstrumentoProcessualCriar(**DADOS_APOSTILAMENTO_BASE, **DADOS_REAJUSTE)
    assert instrumento.reajuste_indice_nome == "IPCA-E"
    assert instrumento.valor_delta is None  # calculado pelo backend, não enviado


def test_apostilamento_de_reajuste_recusa_campos_pela_metade():
    dados_incompletos = dict(DADOS_REAJUSTE)
    del dados_incompletos["reajuste_data_fim"]
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**DADOS_APOSTILAMENTO_BASE, **dados_incompletos)


def test_apostilamento_de_reajuste_recusa_valor_delta_junto():
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**DADOS_APOSTILAMENTO_BASE, **DADOS_REAJUSTE, valor_delta="500.00")


def test_apostilamento_de_reajuste_exige_data_fim_apos_inicio():
    dados = dict(DADOS_REAJUSTE)
    dados["reajuste_data_fim"] = date(2025, 1, 1)  # antes do início
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**DADOS_APOSTILAMENTO_BASE, **dados)


def test_apostilamento_nao_aceita_datas_de_vigencia():
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(
            **DADOS_APOSTILAMENTO_BASE,
            data_inicio_vigencia=date(2026, 1, 1),
            data_fim_vigencia=date(2026, 12, 31),
        )


def test_acrescimo_valor_nao_aceita_campos_de_reajuste():
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(
            tipo="acrescimo_valor",
            fundamentacao="Lei 13.303/16, art. 81",
            valor_delta="1000.00",
            reajuste_indice_nome="IPCA-E",
        )
