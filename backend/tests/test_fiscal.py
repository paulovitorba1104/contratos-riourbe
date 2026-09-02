import pytest
from pydantic import ValidationError

from app.schemas.fiscal import FiscalAtualizar, FiscalCriar

MATRICULA_VALIDA = "12/345.678-9"


def test_fiscal_aceita_sem_cpf():
    fiscal = FiscalCriar(nome="João da Silva", matricula=MATRICULA_VALIDA)
    assert fiscal.cpf is None


def test_fiscal_aceita_string_vazia_como_sem_cpf():
    fiscal = FiscalCriar(nome="João da Silva", matricula=MATRICULA_VALIDA, cpf="")
    assert fiscal.cpf is None


def test_fiscal_normaliza_cpf_valido():
    fiscal = FiscalCriar(nome="João da Silva", matricula=MATRICULA_VALIDA, cpf="529.982.247-25")
    assert fiscal.cpf == "52998224725"


def test_fiscal_rejeita_cpf_invalido():
    with pytest.raises(ValidationError):
        FiscalCriar(nome="João da Silva", matricula=MATRICULA_VALIDA, cpf="111.111.111-11")


def test_fiscal_exige_matricula():
    with pytest.raises(ValidationError):
        FiscalCriar(nome="João da Silva", matricula="")


def test_fiscal_normaliza_matricula_formatada():
    fiscal = FiscalCriar(nome="João da Silva", matricula=MATRICULA_VALIDA)
    assert fiscal.matricula == "123456789"


def test_fiscal_rejeita_matricula_com_tamanho_errado():
    with pytest.raises(ValidationError):
        FiscalCriar(nome="João da Silva", matricula="123")


def test_fiscal_atualizar_aceita_campos_parciais():
    dados = FiscalAtualizar(nome="Novo Nome")
    assert dados.model_dump(exclude_unset=True) == {"nome": "Novo Nome"}


def test_fiscal_atualizar_normaliza_matricula():
    dados = FiscalAtualizar(matricula=MATRICULA_VALIDA)
    assert dados.matricula == "123456789"


def test_fiscal_atualizar_rejeita_cpf_invalido():
    with pytest.raises(ValidationError):
        FiscalAtualizar(cpf="111.111.111-11")
