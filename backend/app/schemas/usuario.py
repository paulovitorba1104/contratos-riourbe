import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import cpf_valido, normalizar_cpf, validar_politica_senha
from app.models.usuario import ModuloSistema, PapelUsuario, SituacaoUsuario


class _DadosPessoais(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    matricula: str = Field(..., min_length=1, max_length=30)
    cpf: str
    email: EmailStr

    # "before" para o tamanho mínimo valer já sem os espaços.
    @field_validator("nome", "matricula", mode="before")
    @classmethod
    def _sem_espacos_nas_pontas(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @field_validator("cpf")
    @classmethod
    def _valida_cpf(cls, v: str) -> str:
        if not cpf_valido(v):
            raise ValueError("CPF inválido.")
        return normalizar_cpf(v)


class _Acesso(BaseModel):
    papel: PapelUsuario = PapelUsuario.OPERADOR
    modulos: list[ModuloSistema] = []

    @field_validator("modulos")
    @classmethod
    def _sem_repeticao(cls, v: list[ModuloSistema]) -> list[ModuloSistema]:
        return list(dict.fromkeys(v))


class SolicitacaoCadastro(_DadosPessoais):
    """Pedido de acesso feito pelo próprio usuário na tela de login. Entra como
    operador sem módulo nenhum; papel e módulos quem define é o administrador."""

    senha: str

    @field_validator("senha")
    @classmethod
    def _valida_senha(cls, v: str) -> str:
        validar_politica_senha(v)
        return v


class UsuarioCriar(_DadosPessoais, _Acesso):
    """Cadastro feito pelo administrador: já nasce aprovado, com senha
    temporária gerada pelo sistema (troca obrigatória no primeiro acesso)."""


class AcessoUsuario(_Acesso):
    """Papel e módulos — usado para aprovar um pedido e para editar o acesso."""


class UsuarioSaida(BaseModel):
    id: uuid.UUID
    nome: str
    matricula: str | None
    cpf: str
    email: str
    papel: PapelUsuario
    ativo: bool
    trocar_senha_obrigatorio: bool
    modulos: list[str]
    situacao: SituacaoUsuario
    criado_em: datetime

    model_config = {"from_attributes": True}


class SenhaTemporariaSaida(BaseModel):
    usuario: UsuarioSaida
    senha_temporaria: str
