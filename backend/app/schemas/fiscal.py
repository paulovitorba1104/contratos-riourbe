import uuid
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.security import cpf_valido, normalizar_cpf
from app.core.validadores import matricula_valida, normalizar_matricula


def _valida_cpf_opcional(v: str | None) -> str | None:
    if v is None or v.strip() == "":
        return None
    if not cpf_valido(v):
        raise ValueError("CPF inválido.")
    return normalizar_cpf(v)


def _valida_matricula(v: str) -> str:
    if not matricula_valida(v):
        raise ValueError("Matrícula inválida — formato esperado: 00/000.000-0.")
    return normalizar_matricula(v)


class FiscalCriar(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    matricula: str
    cpf: str | None = None

    @field_validator("matricula")
    @classmethod
    def _valida_matricula_criar(cls, v: str) -> str:
        return _valida_matricula(v)

    @field_validator("cpf")
    @classmethod
    def _valida_cpf_criar(cls, v: str | None) -> str | None:
        return _valida_cpf_opcional(v)


class FiscalAtualizar(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=200)
    matricula: str | None = None
    cpf: str | None = None
    ativo: bool | None = None

    @field_validator("matricula")
    @classmethod
    def _valida_matricula_atualizar(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _valida_matricula(v)

    @field_validator("cpf")
    @classmethod
    def _valida_cpf_atualizar(cls, v: str | None) -> str | None:
        return _valida_cpf_opcional(v)


class FiscalSaida(BaseModel):
    id: uuid.UUID
    nome: str
    matricula: str
    cpf: str | None
    ativo: bool

    model_config = {"from_attributes": True}


class FiscalVincular(BaseModel):
    """Designa um fiscal para o contrato — início do vínculo de fiscalização."""

    fiscal_id: uuid.UUID
    data_inicio: date


class FiscalEncerrarVinculo(BaseModel):
    """Encerra um vínculo de fiscalização ativo (ex.: substituição do fiscal)."""

    data_fim: date


class FiscalVinculoSaida(BaseModel):
    id: uuid.UUID
    fiscal_id: uuid.UUID
    nome: str
    matricula: str
    data_inicio: date
    data_fim: date | None

    model_config = {"from_attributes": True}
