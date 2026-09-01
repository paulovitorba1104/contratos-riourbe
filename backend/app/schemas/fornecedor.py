import uuid

from pydantic import BaseModel, Field, field_validator

from app.core.validadores import cnpj_valido, normalizar_cnpj


class FornecedorCriar(BaseModel):
    razao_social: str = Field(..., min_length=2, max_length=255)
    cnpj: str

    @field_validator("cnpj")
    @classmethod
    def _valida_cnpj(cls, v: str) -> str:
        if not cnpj_valido(v):
            raise ValueError("CNPJ inválido.")
        return normalizar_cnpj(v)


class FornecedorSaida(BaseModel):
    id: uuid.UUID
    razao_social: str
    cnpj: str

    model_config = {"from_attributes": True}
