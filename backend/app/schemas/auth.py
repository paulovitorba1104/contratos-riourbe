import uuid

from pydantic import BaseModel, Field

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

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    usuario: UsuarioPublico
