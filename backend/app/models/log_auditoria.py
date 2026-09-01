import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class LogAuditoria(Base):
    """Log de auditoria transversal — padrão reaproveitado do sistema de Faturas.

    Registra quem fez o quê, quando, em qual registro (seção 13 do plano).
    """

    __tablename__ = "log_auditoria"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.usuarios.id", ondelete="SET NULL"), nullable=True
    )
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    entidade: Mapped[str] = mapped_column(String(100), nullable=False)
    entidade_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detalhes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
