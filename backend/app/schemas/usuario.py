import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import cpf_valido, normalizar_cpf, validar_politica_senha
from app.models.usuario import PapelUsuario


class UsuarioCriar(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    matricula: str | None = Field(None, max_length=30)
    cpf: str
    email: EmailStr
    senha: str
    papel: PapelUsuario = PapelUsuario.OPERADOR

    @field_validator("cpf")
    @classmethod
    def _valida_cpf(cls, v: str) -> str:
        if not cpf_valido(v):
            raise ValueError("CPF inválido.")
        return normalizar_cpf(v)

    @field_validator("senha")
    @classmethod
    def _valida_senha(cls, v: str) -> str:
        validar_politica_senha(v)
        return v


class UsuarioAtualizarPapel(BaseModel):
    papel: PapelUsuario


class UsuarioSaida(BaseModel):
    id: uuid.UUID
    nome: str
    matricula: str | None
    cpf: str
    email: str
    papel: PapelUsuario
    ativo: bool

    model_config = {"from_attributes": True}
