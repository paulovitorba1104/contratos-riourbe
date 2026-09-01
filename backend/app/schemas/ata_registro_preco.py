import uuid
from datetime import date

from pydantic import BaseModel, Field


class AtaRegistroPrecoCriar(BaseModel):
    orgao: str = Field(..., max_length=255)
    numero_ata: str = Field(..., max_length=50)
    objeto: str
    data_validade: date
    disponivel_para_adesao: bool = True
    observacoes: str | None = None


class AtaRegistroPrecoAtualizar(BaseModel):
    disponivel_para_adesao: bool | None = None
    observacoes: str | None = None


class AtaRegistroPrecoSaida(BaseModel):
    id: uuid.UUID
    orgao: str
    numero_ata: str
    objeto: str
    data_validade: date
    disponivel_para_adesao: bool
    observacoes: str | None

    model_config = {"from_attributes": True}
