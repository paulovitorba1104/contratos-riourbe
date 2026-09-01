import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AtaRegistroPreco(Base):
    """Ata de registro de preço — lista para adesão (carona), seção 4.6.

    Versão simples para a Fase 1 (Contratos): cadastro manual, sem busca por
    similaridade nem integração externa — isso é escopo da Fase 3
    (Licitação, seção 6.7), que deve estender esta mesma tabela.
    """

    __tablename__ = "atas_registro_preco"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    orgao: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_ata: Mapped[str] = mapped_column(String(50), nullable=False)
    objeto: Mapped[str] = mapped_column(Text, nullable=False)
    data_validade: Mapped[date] = mapped_column(Date, nullable=False)
    disponivel_para_adesao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
