import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.contrato import Contrato


def _valores_enum(enum_cls):
    return [membro.value for membro in enum_cls]


class TipoInstrumento(str, enum.Enum):
    ORIGEM = "origem"
    PRORROGACAO = "prorrogacao"
    ACRESCIMO_VALOR = "acrescimo_valor"
    SUPRESSAO_VALOR = "supressao_valor"
    ALTERACAO_QUALITATIVA = "alteracao_qualitativa"
    REEQUILIBRIO = "reequilibrio"
    APOSTILAMENTO = "apostilamento"
    SUSPENSAO = "suspensao"
    RESCISAO_EXTINCAO = "rescisao_extincao"


# Tipos que redefinem o período de vigência atual (relógio 1)
TIPOS_QUE_DEFINEM_VIGENCIA = {TipoInstrumento.ORIGEM, TipoInstrumento.PRORROGACAO}

# Só estes tipos mudam o status macro do contrato (seção 4.3)
TIPOS_QUE_MUDAM_STATUS_MACRO = {TipoInstrumento.SUSPENSAO, TipoInstrumento.RESCISAO_EXTINCAO}


class SubStatusInstrumento(str, enum.Enum):
    ELABORACAO = "elaboracao"
    PARECER_JURIDICO = "parecer_juridico"
    ASSINATURA = "assinatura"
    PUBLICADO = "publicado"


class FundamentacaoLei(str, enum.Enum):
    LEI_13303_16 = "lei_13303_16"
    LEI_14133_21 = "lei_14133_21"


class InstrumentoProcessual(Base):
    """Instrumento processual — origem ou aditivo de um contrato (seção 4.2).

    Cada instrumento é mapeado a 1 dos 32 modelos RIPM da PGM-Rio, com
    fundamentação legal estruturada (não texto livre) e sub-status próprio
    de tramitação.
    """

    __tablename__ = "instrumentos_processuais"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )

    tipo: Mapped[TipoInstrumento] = mapped_column(
        Enum(TipoInstrumento, name="tipo_instrumento", schema="contratos", values_callable=_valores_enum),
        nullable=False,
    )
    modelo_ripm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contratos.modelos_ripm.id"), nullable=False)

    fundamentacao_lei: Mapped[FundamentacaoLei] = mapped_column(
        Enum(FundamentacaoLei, name="fundamentacao_lei", schema="contratos", values_callable=_valores_enum),
        nullable=False,
    )
    fundamentacao_artigo: Mapped[str] = mapped_column(String(100), nullable=False)

    sub_status: Mapped[SubStatusInstrumento] = mapped_column(
        Enum(
            SubStatusInstrumento,
            name="sub_status_instrumento",
            schema="contratos",
            values_callable=_valores_enum,
        ),
        nullable=False,
        default=SubStatusInstrumento.ELABORACAO,
    )

    numero_documento_sei: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Preenchidos conforme o tipo: origem/prorrogação definem vigência;
    # acréscimo/supressão definem valor_delta; demais tipos podem deixar em branco.
    data_inicio_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_delta: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship(back_populates="instrumentos")
