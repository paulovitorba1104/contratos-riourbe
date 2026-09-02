from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.contrato import ContratoCriar, InstrumentoOrigemCriar

DADOS_BASE = dict(
    numero_contrato="CT-1",
    processo_sei="SEI-1",
    tipo_servico="Serviço X",
    objeto="Objeto do contrato",
    fornecedor_id="00000000-0000-0000-0000-000000000000",
    forma_contratacao="pregao_eletronico",
    data_assinatura_original=date(2024, 1, 10),
    valor_inicial=Decimal("1000.00"),
    fiscais_ids=["00000000-0000-0000-0000-000000000000"],
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
