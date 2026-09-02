import uuid
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.security import cpf_valido, normalizar_cpf


class FiscalCriar(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    matricula: str = Field(..., min_length=1, max_length=30)
    cpf: str | None = None

    @field_validator("cpf")
    @classmethod
    def _valida_cpf_se_informado(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        if not cpf_valido(v):
            raise ValueError("CPF inválido.")
        return normalizar_cpf(v)


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
