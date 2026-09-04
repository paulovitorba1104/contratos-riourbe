import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.faturamento import (
    SituacaoItemConferencia,
    StatusFatura,
    StatusMedicao,
    TipoEventoFatura,
    Tributo,
)

COMPETENCIA = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="AAAA-MM")


# --------------------------------------------------------------------------
# Medições
# --------------------------------------------------------------------------
class MedicaoCriar(BaseModel):
    contrato_id: uuid.UUID
    numero_medicao: str = Field(..., max_length=50)
    competencia: str = COMPETENCIA
    periodo_inicio: date
    periodo_fim: date
    valor_medido: Decimal = Field(..., ge=0)
    observacoes: str | None = None


class MedicaoAtualizar(BaseModel):
    numero_medicao: str | None = Field(None, max_length=50)
    competencia: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    valor_medido: Decimal | None = Field(None, ge=0)
    observacoes: str | None = None


class MedicaoSaida(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    numero_medicao: str
    competencia: str
    periodo_inicio: date
    periodo_fim: date
    valor_medido: Decimal
    status: StatusMedicao
    aprovado_por_nome: str | None = None
    aprovado_em: datetime | None = None
    observacoes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------
# Glosas, retenções, conferência
# --------------------------------------------------------------------------
class GlosaCriar(BaseModel):
    valor: Decimal = Field(..., gt=0)
    motivo: str = Field(..., min_length=3)


class GlosaSaida(BaseModel):
    id: uuid.UUID
    valor: Decimal
    motivo: str
    registrado_por_nome: str
    registrado_em: datetime

    model_config = {"from_attributes": True}


class RetencaoInformada(BaseModel):
    """O que veio na nota, tributo a tributo. O esperado é calculado pelo
    sistema a partir das regras vigentes na data de emissão."""

    tributo: Tributo
    valor_informado: Decimal = Field(..., ge=0)
    observacao: str | None = None


class RetencaoSaida(BaseModel):
    id: uuid.UUID
    tributo: Tributo
    base_calculo: Decimal
    aliquota: Decimal
    valor_esperado: Decimal
    valor_informado: Decimal
    divergente: bool
    observacao: str | None = None

    model_config = {"from_attributes": True}


class RetencaoSugerida(BaseModel):
    """Prévia do cálculo, para a tela já abrir preenchida com o esperado."""

    tributo: Tributo
    descricao: str
    base_legal: str | None
    base_calculo: Decimal
    aliquota: Decimal
    valor_esperado: Decimal


class ItemConferenciaEntrada(BaseModel):
    descricao: str = Field(..., max_length=300)
    obrigatorio: bool = True
    situacao: SituacaoItemConferencia
    observacao: str | None = None
    ordem: int = 0


class ConferenciaCriar(BaseModel):
    modelo_checklist_id: uuid.UUID | None = None
    itens: list[ItemConferenciaEntrada] = Field(..., min_length=1)
    observacoes: str | None = None


class ItemConferenciaSaida(BaseModel):
    id: uuid.UUID
    ordem: int
    descricao: str
    obrigatorio: bool
    situacao: SituacaoItemConferencia
    observacao: str | None = None

    model_config = {"from_attributes": True}


class ConferenciaSaida(BaseModel):
    id: uuid.UUID
    modelo_checklist_id: uuid.UUID | None
    conferido_por_nome: str
    conferido_em: datetime
    observacoes: str | None
    itens: list[ItemConferenciaSaida]

    model_config = {"from_attributes": True}


class EventoSaida(BaseModel):
    id: uuid.UUID
    tipo: TipoEventoFatura
    data_evento: date
    responsavel_nome: str
    observacoes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------
# Faturas
# --------------------------------------------------------------------------
class FaturaCriar(BaseModel):
    contrato_id: uuid.UUID
    medicao_id: uuid.UUID | None = None
    fatura_origem_id: uuid.UUID | None = None
    numero_nota_fiscal: str = Field(..., max_length=50)
    serie: str | None = Field(None, max_length=20)
    numero_processo_sei: str | None = Field(None, max_length=50)
    competencia: str = COMPETENCIA
    data_emissao: date
    data_recebimento: date
    valor_bruto: Decimal = Field(..., gt=0)
    data_vencimento: date | None = None
    observacoes: str | None = None


class FaturaAtualizar(BaseModel):
    """Edição dos dados cadastrais. O status não entra aqui — muda só por
    evento registrado."""

    numero_nota_fiscal: str | None = Field(None, max_length=50)
    serie: str | None = Field(None, max_length=20)
    numero_processo_sei: str | None = Field(None, max_length=50)
    competencia: str | None = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    data_emissao: date | None = None
    data_recebimento: date | None = None
    valor_bruto: Decimal | None = Field(None, gt=0)
    data_vencimento: date | None = None
    data_envio_gco: date | None = None
    data_liquidacao: date | None = None
    medicao_id: uuid.UUID | None = None
    observacoes: str | None = None


class RegistrarEvento(BaseModel):
    """Atesto, pagamento, devolução e cancelamento — cada um move o status."""

    data_evento: date
    observacoes: str | None = None


class FaturaSaida(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    contrato_numero: str
    fornecedor_nome: str
    medicao_id: uuid.UUID | None
    numero_nota_fiscal: str
    serie: str | None
    numero_processo_sei: str | None
    competencia: str
    data_emissao: date
    data_recebimento: date
    data_vencimento: date | None
    data_envio_gco: date | None
    data_liquidacao: date | None
    data_pagamento: date | None
    valor_bruto: Decimal
    valor_glosas: Decimal
    valor_retencoes: Decimal
    valor_liquido: Decimal
    status: StatusFatura
    observacoes: str | None
    alerta_vencimento: str | None
    divergencia_tributaria: bool


class FaturaDetalhada(FaturaSaida):
    fatura_origem_id: uuid.UUID | None
    glosas: list[GlosaSaida]
    retencoes: list[RetencaoSaida]
    conferencias: list[ConferenciaSaida]
    eventos: list[EventoSaida]


class LinhaPainelAnual(BaseModel):
    """Uma linha da matriz contrato × mês — a visão de controle que substitui
    a aba anual da planilha."""

    contrato_id: uuid.UUID
    contrato_numero: str
    fornecedor_nome: str
    vigencia_fim: date | None
    status_contrato: str
    # 12 posições (jan..dez); cada uma traz o status da fatura daquele mês.
    meses: list[str | None]


# --------------------------------------------------------------------------
# Configuração: regras tributárias e modelos de checklist
# --------------------------------------------------------------------------
class RegraTributariaCriar(BaseModel):
    tributo: Tributo
    descricao: str = Field(..., max_length=200)
    base_legal: str | None = Field(None, max_length=200)
    aliquota: Decimal = Field(..., ge=0, le=100)
    percentual_base: Decimal = Field(default=Decimal("100"), gt=0, le=100)
    vigencia_inicio: date
    vigencia_fim: date | None = None


class RegraTributariaAtualizar(BaseModel):
    descricao: str | None = Field(None, max_length=200)
    base_legal: str | None = Field(None, max_length=200)
    aliquota: Decimal | None = Field(None, ge=0, le=100)
    percentual_base: Decimal | None = Field(None, gt=0, le=100)
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    ativo: bool | None = None


class RegraTributariaSaida(BaseModel):
    id: uuid.UUID
    tributo: Tributo
    descricao: str
    base_legal: str | None
    aliquota: Decimal
    percentual_base: Decimal
    vigencia_inicio: date
    vigencia_fim: date | None
    ativo: bool

    model_config = {"from_attributes": True}


class ItemModeloEntrada(BaseModel):
    descricao: str = Field(..., max_length=300)
    obrigatorio: bool = True
    ordem: int = 0


class ModeloChecklistCriar(BaseModel):
    nome: str = Field(..., max_length=200)
    descricao: str | None = None
    itens: list[ItemModeloEntrada] = Field(..., min_length=1)


class ModeloChecklistAtualizar(BaseModel):
    nome: str | None = Field(None, max_length=200)
    descricao: str | None = None
    ativo: bool | None = None
    itens: list[ItemModeloEntrada] | None = None


class ItemModeloSaida(BaseModel):
    id: uuid.UUID
    ordem: int
    descricao: str
    obrigatorio: bool

    model_config = {"from_attributes": True}


class ModeloChecklistSaida(BaseModel):
    id: uuid.UUID
    nome: str
    descricao: str | None
    ativo: bool
    itens: list[ItemModeloSaida]

    model_config = {"from_attributes": True}
