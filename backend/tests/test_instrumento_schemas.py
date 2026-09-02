from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.instrumento import InstrumentoProcessualCriar

DADOS_ORIGEM = dict(
    tipo="origem",
    fundamentacao_lei="lei_13303_16",
    fundamentacao_artigo="art. 1",
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
    dados_sem_fundamentacao = {k: v for k, v in DADOS_ORIGEM.items() if k != "fundamentacao_artigo"}
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**dados_sem_fundamentacao)


def test_instrumento_origem_ainda_exige_datas_de_vigencia():
    dados_sem_datas = {k: v for k, v in DADOS_ORIGEM.items() if k != "data_fim_vigencia"}
    with pytest.raises(ValidationError):
        InstrumentoProcessualCriar(**dados_sem_datas)
