import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.contrato import FormaContratacao, StatusContrato
from app.models.instrumento_processual import FundamentacaoLei
from app.schemas.fiscal import FiscalVinculoSaida
from app.schemas.instrumento import InstrumentoProcessualSaida


class InstrumentoOrigemCriar(BaseModel):
    """O instrumento de Origem — primeiro prazo de vigência do contrato,
    criado junto com o contrato (não depois, como os aditivos). O RIPM aqui é
    o checklist de instrução processual que a jurídica confere na abertura do
    processo; a fundamentação legal (lei + artigo) é a mesma exigida de
    qualquer instrumento que define vigência (seção 4.2)."""

    modelo_ripm_id: uuid.UUID
    fundamentacao_lei: FundamentacaoLei
    fundamentacao_artigo: str = Field(..., max_length=100)
    numero_documento_sei: str | None = Field(None, max_length=50)
    data_inicio_vigencia: date
    data_fim_vigencia: date

    @field_validator("data_fim_vigencia")
    @classmethod
    def _fim_apos_inicio(cls, v: date, info) -> date:
        inicio = info.data.get("data_inicio_vigencia")
        if inicio is not None and v <= inicio:
            raise ValueError("A data de fim de vigência deve ser posterior à data de início.")
        return v


class ContratoCriar(BaseModel):
    numero_contrato: str = Field(..., max_length=50)
    processo_sei: str = Field(..., max_length=50)
    tipo_servico: str = Field(..., max_length=200)
    objeto: str = Field(..., min_length=3)
    fornecedor_id: uuid.UUID
    forma_contratacao: FormaContratacao
    data_assinatura_original: date
    valor_inicial: Decimal = Field(..., gt=0)
    nota_reserva: str | None = None
    nota_empenho: str | None = None
    pt: str | None = None
    nd: str | None = None
    fr: str | None = None
    tipo_patrimonial: str | None = None
    item_patrimonial: str | None = None
    codigo_ccon: str | None = None
    observacoes: str | None = None
    # Prazo de vigência inicial (Relógio 1) — o teto de 5 anos (Relógio 2) só
    # funciona corretamente se o contrato já nascer com esse marco zero;
    # prorrogações depois entram como novos instrumentos na ficha do contrato.
    instrumento_origem: InstrumentoOrigemCriar
    # Fiscal obrigatório — gap identificado na planilha antiga (seção 4.5).
    # Vínculo(s) inicial(is); data_inicio de cada um é a data de assinatura
    # original por padrão do lado do frontend, mas pode ser ajustada.
    fiscais_ids: list[uuid.UUID] = Field(..., min_length=1)


class ContratoAtualizar(BaseModel):
    """Edição geral do contrato — todos os campos opcionais (só atualiza o
    que for enviado). Não inclui `status` (só muda via instrumento
    processual, seção 4.3) nem `fiscais` (têm endpoints próprios, já que são
    vínculos temporais, não um campo simples do contrato)."""

    numero_contrato: str | None = Field(None, max_length=50)
    processo_sei: str | None = Field(None, max_length=50)
    tipo_servico: str | None = Field(None, max_length=200)
    objeto: str | None = Field(None, min_length=3)
    fornecedor_id: uuid.UUID | None = None
    forma_contratacao: FormaContratacao | None = None
    data_assinatura_original: date | None = None
    valor_inicial: Decimal | None = Field(None, gt=0)
    valor_pago: Decimal | None = Field(None, ge=0)
    nota_reserva: str | None = None
    nota_empenho: str | None = None
    pt: str | None = None
    nd: str | None = None
    fr: str | None = None
    tipo_patrimonial: str | None = None
    item_patrimonial: str | None = None
    codigo_ccon: str | None = None
    observacoes: str | None = None


class GarantiaCriar(BaseModel):
    """Registra uma nova entrada no histórico de garantia — nunca sobrescreve
    a anterior (seção sobre o Relógio 3 no README)."""

    data_inicio_garantia: date | None = None
    data_fim_garantia: date | None = None
    observacao: str | None = None

    @field_validator("data_fim_garantia")
    @classmethod
    def _fim_apos_inicio(cls, v: date | None, info) -> date | None:
        inicio = info.data.get("data_inicio_garantia")
        if v is not None and inicio is not None and v <= inicio:
            raise ValueError("A data de fim da garantia deve ser posterior à data de início.")
        return v


class GarantiaSaida(BaseModel):
    id: uuid.UUID
    data_inicio_garantia: date | None
    data_fim_garantia: date | None
    observacao: str | None
    registrado_por_nome: str
    registrado_em: datetime

    model_config = {"from_attributes": True}


class ContratoAtualizarPagamento(BaseModel):
    valor_pago: Decimal = Field(..., ge=0)


class ContratoSaida(BaseModel):
    id: uuid.UUID
    numero_contrato: str
    processo_sei: str
    tipo_servico: str
    objeto: str
    fornecedor_id: uuid.UUID
    forma_contratacao: FormaContratacao
    status: StatusContrato
    data_assinatura_original: date
    valor_inicial: Decimal
    valor_pago: Decimal
    nota_reserva: str | None
    nota_empenho: str | None
    pt: str | None
    nd: str | None
    fr: str | None
    tipo_patrimonial: str | None
    item_patrimonial: str | None
    codigo_ccon: str | None
    observacoes: str | None
    # Incluídos aqui (não só em ContratoDetalhado) para aparecer já na
    # listagem/dashboard — contratos perto de vencer vigência ou garantia
    # precisam ser visíveis no Kanban, não só na ficha do contrato.
    alerta_vigencia: str | None
    alerta_garantia: str | None

    model_config = {"from_attributes": True}


class ContratoDetalhado(ContratoSaida):
    fiscais: list[FiscalVinculoSaida]
    valor_atualizado: Decimal
    saldo_a_pagar: Decimal
    vigencia_inicio: date | None
    vigencia_fim: date | None
    teto_vigencia: date
    garantia_inicio: date | None
    garantia_fim: date | None
    garantias: list[GarantiaSaida]
    instrumentos: list[InstrumentoProcessualSaida]
