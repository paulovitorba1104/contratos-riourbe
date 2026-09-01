import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ModeloRipm(Base):
    """Modelo de checklist RIPM da PGM-Rio — reaproveita o padrão
    modelos_checklist/conferencias já validado no sistema de Faturas.

    Cadastro fica vazio até a lista oficial dos 32 modelos ser fornecida —
    ver pendência da seção 16 do plano. `itens_checklist` guarda a lista de
    itens do checklist daquele modelo (estrutura livre em JSON, cada módulo
    de conferência decide como usar).
    """

    __tablename__ = "modelos_ripm"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    itens_checklist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
