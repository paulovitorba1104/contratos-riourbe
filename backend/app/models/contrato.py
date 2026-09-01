import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.instrumento_processual import InstrumentoProcessual


class FormaContratacao(str, enum.Enum):
    PREGAO_ELETRONICO = "pregao_eletronico"
    DISPENSA = "dispensa"
    INEXIGIBILIDADE = "inexigibilidade"


class StatusContrato(str, enum.Enum):
    VIGENTE = "vigente"
    SUSPENSO = "suspenso"
    ENCERRADO = "encerrado"


def _valores_enum(enum_cls):
    return [membro.value for membro in enum_cls]


class Contrato(Base):
    """Entidade Contrato — seção 4 do plano de desenvolvimento.

    Nasce de exatamente 1 forma de contratação e acumula N instrumentos
    processuais ao longo do tempo (origem + cada aditivo). O status macro só
    muda via instrumento de suspensão/rescisão — nunca é editado diretamente.
    """

    __tablename__ = "contratos"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Identificação
    processo_sei: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_servico: Mapped[str] = mapped_column(String(200), nullable=False)
    objeto: Mapped[str] = mapped_column(Text, nullable=False)
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.fornecedores.id"), nullable=False)
    forma_contratacao: Mapped[FormaContratacao] = mapped_column(
        Enum(
            FormaContratacao,
            name="forma_contratacao",
            schema="contratos",
            values_callable=_valores_enum,
        ),
        nullable=False,
    )

    # Status macro — calculado, nunca editado diretamente (seção 4.3)
    status: Mapped[StatusContrato] = mapped_column(
        Enum(StatusContrato, name="status_contrato", schema="contratos", values_callable=_valores_enum),
        nullable=False,
        default=StatusContrato.VIGENTE,
    )

    # Relógio 2: tempo total desde a assinatura original — teto rígido de 5 anos
    data_assinatura_original: Mapped[date] = mapped_column(Date, nullable=False)

    # Financeiro
    valor_inicial: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    valor_pago: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    nota_reserva: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nota_empenho: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Orçamentário/contábil
    pt: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nd: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_patrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_patrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_ccon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relógio 3: garantia contratual — independente da vigência
    data_inicio_garantia: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_garantia: Mapped[date | None] = mapped_column(Date, nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    instrumentos: Mapped[list["InstrumentoProcessual"]] = relationship(
        back_populates="contrato", order_by="InstrumentoProcessual.criado_em", cascade="all, delete-orphan"
    )
    fiscais: Mapped[list["ContratoFiscal"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )


class ContratoFiscal(Base):
    """Fiscal(is) do contrato — obrigatório, gap identificado na planilha antiga."""

    __tablename__ = "contrato_fiscais"
    __table_args__ = {"schema": "contratos"}

    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), primary_key=True)

    contrato: Mapped["Contrato"] = relationship(back_populates="fiscais")
