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
    from app.models.usuario import Usuario


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


class InstrumentoProcessual(Base):
    """Instrumento processual — origem ou aditivo de um contrato (seção 4.2).

    Cada instrumento é mapeado a 1 dos 32 modelos RIPM da PGM-Rio, com
    sub-status próprio de tramitação.
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
    # RIPM é só um checklist de instrução processual (apoio administrativo,
    # não documento jurídico como o próprio instrumento) — por isso é opcional.
    modelo_ripm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contratos.modelos_ripm.id"), nullable=True
    )

    # Texto livre (não estruturado) — normalmente uma lei e artigo (ex.:
    # "Lei 13.303/16, art. 71"), mas pode ser um decreto, portaria ou outro
    # ato normativo, então não vale a pena travar num enum de leis fixas.
    fundamentacao: Mapped[str] = mapped_column(String(300), nullable=False)

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

    # Datas do próprio instrumento (não confundir com criado_em, que é só
    # quando alguém cadastrou no sistema) — preenchidas à mão, geralmente
    # depois, conforme o processo avança: quando foi de fato assinado/
    # formalizado, e quando saiu publicado (ex.: Diário Oficial). Nenhuma
    # das duas é obrigatória nem amarrada ao sub_status abaixo.
    data_formalizacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_publicacao: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Preenchidos conforme o tipo: origem/prorrogação definem vigência;
    # acréscimo/supressão/apostilamento (quando é de reajuste) definem valor_delta;
    # demais tipos podem deixar em branco.
    data_inicio_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_delta: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)

    # Preenchidos só quando o apostilamento é de reajuste (seção 4.6) — o
    # cálculo mês a mês fica em app/services/reajuste.py, derivado a partir
    # destes campos, não persistido linha a linha. Campos próprios (em vez de
    # reaproveitar data_inicio_vigencia/data_fim_vigencia) para não confundir
    # com o marco de vigência do contrato: são conceitos diferentes — o
    # reajuste redefine o valor mensal, não o período de vigência.
    reajuste_indice_nome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reajuste_indice_atual: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)  # I
    reajuste_indice_base: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)  # Io
    reajuste_valor_mensal_antigo: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)  # Po
    reajuste_valor_mensal_novo: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    reajuste_data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    reajuste_data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship(back_populates="instrumentos")
    anexos: Mapped[list["AnexoInstrumento"]] = relationship(
        back_populates="instrumento", order_by="AnexoInstrumento.enviado_em", cascade="all, delete-orphan"
    )


class AnexoInstrumento(Base):
    """Arquivo anexado a um instrumento processual (contrato, termo aditivo,
    apostilamento etc.) — visualização rápida sem precisar ir atrás do
    processo físico/SEI. Guardado em disco local (`app/uploads/`, fora do
    controle de versão); em deploy sem disco persistente (ex.: Railway sem
    volume configurado) os arquivos não sobrevivem a um redeploy — ver nota
    no README."""

    __tablename__ = "anexos_instrumento"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    instrumento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.instrumentos_processuais.id", ondelete="CASCADE"), nullable=False
    )
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    # Caminho relativo dentro do diretório de uploads — nunca o caminho
    # absoluto do servidor (evita vazar estrutura de disco em respostas/logs).
    caminho_relativo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(nullable=False)

    enviado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    enviado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    instrumento: Mapped["InstrumentoProcessual"] = relationship(back_populates="anexos")
    enviado_por: Mapped["Usuario"] = relationship()
