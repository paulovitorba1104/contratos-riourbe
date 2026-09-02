import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.contrato import FormaContratacao, StatusContrato
from app.schemas.fiscal import FiscalVinculoSaida
from app.schemas.instrumento import InstrumentoProcessualSaida


class ContratoCriar(BaseModel):
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
    # Fiscal obrigatório — gap identificado na planilha antiga (seção 4.5).
    # Vínculo(s) inicial(is); data_inicio de cada um é a data de assinatura
    # original por padrão do lado do frontend, mas pode ser ajustada.
    fiscais_ids: list[uuid.UUID] = Field(..., min_length=1)


class ContratoAtualizarGarantia(BaseModel):
    data_inicio_garantia: date | None = None
    data_fim_garantia: date | None = None

    @field_validator("data_fim_garantia")
    @classmethod
    def _fim_apos_inicio(cls, v: date | None, info) -> date | None:
        inicio = info.data.get("data_inicio_garantia")
        if v is not None and inicio is not None and v <= inicio:
            raise ValueError("A data de fim da garantia deve ser posterior à data de início.")
        return v


class ContratoAtualizarPagamento(BaseModel):
    valor_pago: Decimal = Field(..., ge=0)


class ContratoSaida(BaseModel):
    id: uuid.UUID
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
    data_inicio_garantia: date | None
    data_fim_garantia: date | None
    observacoes: str | None

    model_config = {"from_attributes": True}


class ContratoDetalhado(ContratoSaida):
    fiscais: list[FiscalVinculoSaida]
    valor_atualizado: Decimal
    saldo_a_pagar: Decimal
    vigencia_inicio: date | None
    vigencia_fim: date | None
    teto_vigencia: date
    alerta_vigencia: str | None
    alerta_garantia: str | None
    instrumentos: list[InstrumentoProcessualSaida]
