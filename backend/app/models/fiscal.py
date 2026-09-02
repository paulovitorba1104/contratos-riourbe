import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Fiscal(Base):
    """Cadastro de fiscais de contrato — dado mestre próprio, independente de
    usuário do sistema (nem todo fiscal tem login). Vive em 'core' por ser
    transversal (Contratos hoje, Faturas/Fiscalização depois).

    Identificado pela matrícula (obrigatória e única); CPF é opcional.
    """

    __tablename__ = "fiscais"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    matricula: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
