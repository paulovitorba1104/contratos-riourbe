import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class PapelUsuario(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    OPERADOR = "operador"


class Usuario(Base):
    """Usuário do sistema. Papel global (não por módulo) — seção 13 do plano."""

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

    # Corte de revogação server-side: qualquer token com iat anterior é rejeitado.
    sessoes_validas_apos: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
