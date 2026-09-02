import pytest
from pydantic import ValidationError

from app.schemas.fiscal import FiscalCriar


def test_fiscal_aceita_sem_cpf():
    fiscal = FiscalCriar(nome="João da Silva", matricula="12345")
    assert fiscal.cpf is None


def test_fiscal_aceita_string_vazia_como_sem_cpf():
    fiscal = FiscalCriar(nome="João da Silva", matricula="12345", cpf="")
    assert fiscal.cpf is None


def test_fiscal_normaliza_cpf_valido():
    fiscal = FiscalCriar(nome="João da Silva", matricula="12345", cpf="529.982.247-25")
    assert fiscal.cpf == "52998224725"


def test_fiscal_rejeita_cpf_invalido():
    with pytest.raises(ValidationError):
        FiscalCriar(nome="João da Silva", matricula="12345", cpf="111.111.111-11")


def test_fiscal_exige_matricula():
    with pytest.raises(ValidationError):
        FiscalCriar(nome="João da Silva", matricula="")
