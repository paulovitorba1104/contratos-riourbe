import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.contrato import Contrato
    from app.models.usuario import Usuario


class StatusMedicao(str, enum.Enum):
    EM_ELABORACAO = "em_elaboracao"
    APROVADA = "aprovada"
    REJEITADA = "rejeitada"


class StatusFatura(str, enum.Enum):
    """Etapas do controle da fatura na Rio-Urbe. O módulo acompanha e registra
    o andamento — a liquidação em si é ato de outro setor, fora deste sistema,
    então não existe etapa de liquidação aqui. As quatro primeiras são o
    caminho normal (recebida → conferência → atesto → paga, precedidas da
    medição quando o contrato exige); as duas últimas são saídas de exceção."""

    RECEBIDA = "recebida"
    EM_CONFERENCIA = "em_conferencia"
    CONFERIDA = "conferida"
    ATESTADA = "atestada"
    PAGA = "paga"
    DEVOLVIDA = "devolvida"
    CANCELADA = "cancelada"


class TipoEventoFatura(str, enum.Enum):
    RECEBIMENTO = "recebimento"
    CONFERENCIA = "conferencia"
    ATESTO = "atesto"
    PAGAMENTO = "pagamento"
    DEVOLUCAO = "devolucao"
    CANCELAMENTO = "cancelamento"


class Tributo(str, enum.Enum):
    IRRF = "irrf"
    INSS = "inss"
    ISS = "iss"
    PIS = "pis"
    COFINS = "cofins"
    CSLL = "csll"


class SituacaoItemConferencia(str, enum.Enum):
    CONFORME = "conforme"
    NAO_CONFORME = "nao_conforme"
    NAO_APLICAVEL = "nao_aplicavel"


def _valores_enum(enum_cls):
    return [membro.value for membro in enum_cls]


# Tipo compartilhado por `regras_tributarias` e `retencoes_fatura` — a mesma
# instância nas duas tabelas para o Postgres criar o tipo uma vez só.
TRIBUTO_ENUM = Enum(Tributo, name="tributo", schema="faturas", values_callable=_valores_enum)


class MedicaoContrato(Base):
    """Boletim de medição do período — usado em obras e serviços continuados,
    onde o fornecedor só emite a nota depois que o período executado é medido
    e aprovado. Contratos de compra pontual não passam por aqui (o contrato
    marca isso em `exige_medicao`)."""

    __tablename__ = "medicoes"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    numero_medicao: Mapped[str] = mapped_column(String(50), nullable=False)
    competencia: Mapped[str] = mapped_column(String(7), nullable=False)  # AAAA-MM
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False)
    valor_medido: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)

    status: Mapped[StatusMedicao] = mapped_column(
        Enum(StatusMedicao, name="status_medicao", schema="faturas", values_callable=_valores_enum),
        nullable=False,
        default=StatusMedicao.EM_ELABORACAO,
    )
    aprovado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("core.usuarios.id"), nullable=True
    )
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship()
    aprovado_por: Mapped["Usuario | None"] = relationship()


class Fatura(Base):
    """Nota fiscal vinculada a um contrato. O status nunca é editado
    diretamente — muda a cada evento registrado (`EventoFatura`), mesmo
    princípio do status macro do contrato, que só muda via instrumento."""

    __tablename__ = "faturas"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    # Preenchida quando o contrato exige medição — a nota nasce de um período medido.
    medicao_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("faturas.medicoes.id", ondelete="SET NULL"), nullable=True
    )
    # Preenchida quando esta nota é a reapresentação de uma que foi devolvida,
    # preservando o rastro entre as duas.
    fatura_origem_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("faturas.faturas.id", ondelete="SET NULL"), nullable=True
    )

    numero_nota_fiscal: Mapped[str] = mapped_column(String(50), nullable=False)
    serie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Cada fatura tramita no seu próprio processo administrativo — não é o
    # processo do contrato (ex.: 006700.000249/2026-51).
    numero_processo_sei: Mapped[str | None] = mapped_column(String(50), nullable=True)
    competencia: Mapped[str] = mapped_column(String(7), nullable=False)  # AAAA-MM
    data_emissao: Mapped[date] = mapped_column(Date, nullable=False)
    data_recebimento: Mapped[date] = mapped_column(Date, nullable=False)

    valor_bruto: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)

    status: Mapped[StatusFatura] = mapped_column(
        Enum(StatusFatura, name="status_fatura", schema="faturas", values_callable=_valores_enum),
        nullable=False,
        default=StatusFatura.RECEBIDA,
    )

    # Datas de acompanhamento. O envio à GCO e a liquidação são atos de outros
    # setores — aqui só ficam registrados, como já era feito na planilha de
    # controle, sem virarem etapas do fluxo.
    data_vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_envio_gco: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_liquidacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship()
    medicao: Mapped["MedicaoContrato | None"] = relationship()

    glosas: Mapped[list["GlosaFatura"]] = relationship(
        back_populates="fatura", order_by="GlosaFatura.registrado_em", cascade="all, delete-orphan"
    )
    retencoes: Mapped[list["RetencaoFatura"]] = relationship(
        back_populates="fatura", order_by="RetencaoFatura.criado_em", cascade="all, delete-orphan"
    )
    eventos: Mapped[list["EventoFatura"]] = relationship(
        back_populates="fatura", order_by="EventoFatura.criado_em", cascade="all, delete-orphan"
    )
    conferencias: Mapped[list["ConferenciaFatura"]] = relationship(
        back_populates="fatura", order_by="ConferenciaFatura.conferido_em", cascade="all, delete-orphan"
    )


class GlosaFatura(Base):
    """Abatimento por serviço não prestado. Cada glosa é uma linha nova, nunca
    sobrescrita — mesmo princípio do histórico de garantia contratual."""

    __tablename__ = "glosas"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.faturas.id", ondelete="CASCADE"), nullable=False
    )
    valor: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)

    registrado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fatura: Mapped["Fatura"] = relationship(back_populates="glosas")
    registrado_por: Mapped["Usuario"] = relationship()


class RegraTributaria(Base):
    """Parâmetro fiscal configurável — alíquota, base e fundamentação legal de
    cada tributo retido. Fica em tabela justamente para que mudança de
    legislação seja mudança de cadastro, não nova versão do sistema. A
    vigência permite conferir uma nota antiga pela regra que valia na época."""

    __tablename__ = "regras_tributarias"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tributo: Mapped[Tributo] = mapped_column(TRIBUTO_ENUM, nullable=False)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    base_legal: Mapped[str | None] = mapped_column(String(200), nullable=True)

    aliquota: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    # Fração do valor bruto que compõe a base de cálculo (100 = base cheia).
    percentual_base: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=100)

    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RetencaoFatura(Base):
    """Um tributo conferido numa fatura: o que o sistema calculou a partir da
    regra vigente (`valor_esperado`) contra o que veio na nota
    (`valor_informado`). Divergência não trava o fluxo — exige justificativa."""

    __tablename__ = "retencoes_fatura"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.faturas.id", ondelete="CASCADE"), nullable=False
    )
    tributo: Mapped[Tributo] = mapped_column(TRIBUTO_ENUM, nullable=False)
    base_calculo: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    aliquota: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    valor_esperado: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    valor_informado: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fatura: Mapped["Fatura"] = relationship(back_populates="retencoes")


class ModeloChecklist(Base):
    """Lista reutilizável de documentos/verificações exigidos na conferência —
    contratos diferentes exigem documentos diferentes. Mesmo padrão dos
    modelos RIPM do módulo de Contratos."""

    __tablename__ = "modelos_checklist"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    itens: Mapped[list["ItemModeloChecklist"]] = relationship(
        back_populates="modelo", order_by="ItemModeloChecklist.ordem", cascade="all, delete-orphan"
    )


class ItemModeloChecklist(Base):
    __tablename__ = "itens_modelo_checklist"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    modelo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.modelos_checklist.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    # Item obrigatório não conforme trava o avanço da fatura para o atesto.
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    modelo: Mapped["ModeloChecklist"] = relationship(back_populates="itens")


class ConferenciaFatura(Base):
    """O checklist preenchido de uma fatura — quem conferiu, quando, com qual
    modelo e o resultado item a item."""

    __tablename__ = "conferencias"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.faturas.id", ondelete="CASCADE"), nullable=False
    )
    modelo_checklist_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("faturas.modelos_checklist.id", ondelete="SET NULL"), nullable=True
    )
    conferido_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    conferido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    fatura: Mapped["Fatura"] = relationship(back_populates="conferencias")
    conferido_por: Mapped["Usuario"] = relationship()
    itens: Mapped[list["ItemConferencia"]] = relationship(
        back_populates="conferencia", order_by="ItemConferencia.ordem", cascade="all, delete-orphan"
    )


class ItemConferencia(Base):
    """Resultado de um item do checklist. A descrição é copiada do modelo no
    momento da conferência — se o modelo mudar depois, o que foi conferido
    naquele dia continua registrado como estava."""

    __tablename__ = "itens_conferencia"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conferencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.conferencias.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    situacao: Mapped[SituacaoItemConferencia] = mapped_column(
        Enum(
            SituacaoItemConferencia,
            name="situacao_item_conferencia",
            schema="faturas",
            values_callable=_valores_enum,
        ),
        nullable=False,
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    conferencia: Mapped["ConferenciaFatura"] = relationship(back_populates="itens")


class EventoFatura(Base):
    """Linha do tempo do fluxo. Cada evento registrado é o que move o status da
    fatura — não existe editar status na mão."""

    __tablename__ = "eventos_fatura"
    __table_args__ = {"schema": "faturas"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fatura_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faturas.faturas.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[TipoEventoFatura] = mapped_column(
        Enum(
            TipoEventoFatura, name="tipo_evento_fatura", schema="faturas", values_callable=_valores_enum
        ),
        nullable=False,
    )
    data_evento: Mapped[date] = mapped_column(Date, nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fatura: Mapped["Fatura"] = relationship(back_populates="eventos")
    responsavel: Mapped["Usuario"] = relationship()
