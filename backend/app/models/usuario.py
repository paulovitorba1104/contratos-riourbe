import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import false, func

from app.db.base import Base


class PapelUsuario(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    OPERADOR = "operador"


class ModuloSistema(str, enum.Enum):
    """Módulos que um operador pode receber. Administrador acessa todos sem
    precisar estar em lista nenhuma. Módulo novo = valor novo aqui (a coluna
    guarda texto, então não precisa de migração)."""

    CONTRATOS = "contratos"
    FATURAS = "faturas"


ROTULOS_MODULO = {
    ModuloSistema.CONTRATOS: "Contratos",
    ModuloSistema.FATURAS: "Faturas",
}


class SituacaoUsuario(str, enum.Enum):
    PENDENTE = "pendente"  # pediu acesso pela tela de login, aguarda administrador
    RECUSADO = "recusado"
    ATIVO = "ativo"
    DESATIVADO = "desativado"


class Usuario(Base):
    """Usuário do sistema. Administrador acessa todos os módulos; operador só os
    de `modulos`, definidos por um administrador."""

    __tablename__ = "usuarios"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    matricula: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[PapelUsuario] = mapped_column(
        Enum(
            PapelUsuario,
            name="papel_usuario",
            schema="core",
            values_callable=lambda enum_cls: [membro.value for membro in enum_cls],
        ),
        nullable=False,
        default=PapelUsuario.OPERADOR,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    modulos: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list, server_default=text("'{}'")
    )
    # Nulo = cadastro feito pela tela de login ainda não aprovado (ou recusado).
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Ligado quando a senha atual é uma temporária gerada por terceiro (admin ou
    # script de resgate): até o próprio usuário trocar, a API só aceita trocar a senha.
    trocar_senha_obrigatorio: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    # Corte de revogação server-side: qualquer token com iat anterior é rejeitado.
    sessoes_validas_apos: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def situacao(self) -> SituacaoUsuario:
        if self.aprovado_em is None:
            return SituacaoUsuario.PENDENTE if self.ativo else SituacaoUsuario.RECUSADO
        return SituacaoUsuario.ATIVO if self.ativo else SituacaoUsuario.DESATIVADO

    def pode_acessar(self, modulo: ModuloSistema) -> bool:
        return self.papel == PapelUsuario.ADMINISTRADOR or modulo.value in (self.modulos or [])
