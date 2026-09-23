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


class FornecedorAtualizar(BaseModel):
    razao_social: str | None = Field(None, min_length=2, max_length=255)
    cnpj: str | None = None
    ativo: bool | None = None

    @field_validator("cnpj")
    @classmethod
    def _valida_cnpj_atualizar(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not cnpj_valido(v):
            raise ValueError("CNPJ inválido.")
        return normalizar_cnpj(v)


class FornecedorSaida(BaseModel):
    id: uuid.UUID
    razao_social: str
    cnpj: str
    ativo: bool

    model_config = {"from_attributes": True}


class ConsultaCnpjSaida(BaseModel):
    """Prévia da consulta à Receita Federal (via BrasilAPI) antes de salvar
    — usada para autopreencher a razão social e mostrar a situação
    cadastral enquanto o CNPJ é digitado. `encontrado=False` quando a
    consulta não pôde ser feita (API fora do ar, CNPJ não encontrado) — não
    bloqueia o cadastro, o formulário simplesmente não autopreenche."""

    encontrado: bool
    razao_social: str | None = None
    situacao_cadastral: str | None = None
    ativo: bool | None = None
