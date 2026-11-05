import uuid

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import validar_politica_senha
from app.models.usuario import PapelUsuario


class LoginRequest(BaseModel):
    identificador: str = Field(..., description="Matrícula funcional ou CPF")
    senha: str


class UsuarioPublico(BaseModel):
    id: uuid.UUID
    nome: str
    matricula: str | None
    cpf: str
    email: str
    papel: PapelUsuario
    ativo: bool
    trocar_senha_obrigatorio: bool
    modulos: list[str]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    usuario: UsuarioPublico


class TrocarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def _valida_politica(cls, v: str) -> str:
        validar_politica_senha(v)
        return v

    @model_validator(mode="after")
    def _nova_diferente_da_atual(self) -> "TrocarSenhaRequest":
        if self.nova_senha == self.senha_atual:
            raise ValueError("A nova senha precisa ser diferente da atual.")
        return self
