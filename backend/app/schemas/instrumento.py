import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.instrumento_processual import (
    TIPOS_QUE_DEFINEM_VIGENCIA,
    FundamentacaoLei,
    SubStatusInstrumento,
    TipoInstrumento,
)


class InstrumentoProcessualCriar(BaseModel):
    tipo: TipoInstrumento
    modelo_ripm_id: uuid.UUID
    fundamentacao_lei: FundamentacaoLei
    fundamentacao_artigo: str = Field(..., max_length=100)
    numero_documento_sei: str | None = Field(None, max_length=50)
    data_inicio_vigencia: date | None = None
    data_fim_vigencia: date | None = None
    valor_delta: Decimal | None = None
    observacoes: str | None = None

    @model_validator(mode="after")
    def _valida_campos_por_tipo(self) -> "InstrumentoProcessualCriar":
        if self.tipo in TIPOS_QUE_DEFINEM_VIGENCIA:
            if self.data_inicio_vigencia is None or self.data_fim_vigencia is None:
                raise ValueError(
                    "Instrumentos de origem/prorrogação exigem data de início e fim de vigência."
                )
            if self.data_fim_vigencia <= self.data_inicio_vigencia:
                raise ValueError("A data de fim de vigência deve ser posterior à data de início.")
            if self.valor_delta is not None:
                raise ValueError("Instrumentos de origem/prorrogação não têm valor_delta.")
        elif self.tipo == TipoInstrumento.ACRESCIMO_VALOR:
            if self.valor_delta is None or self.valor_delta <= 0:
                raise ValueError("Acréscimo de valor exige valor_delta positivo.")
            self._exige_sem_vigencia()
        elif self.tipo == TipoInstrumento.SUPRESSAO_VALOR:
            if self.valor_delta is None or self.valor_delta >= 0:
                raise ValueError("Supressão de valor exige valor_delta negativo.")
            self._exige_sem_vigencia()
        else:
            if self.valor_delta is not None:
                raise ValueError(f"Instrumentos do tipo '{self.tipo.value}' não têm valor_delta.")
            self._exige_sem_vigencia()
        return self

    def _exige_sem_vigencia(self) -> None:
        if self.data_inicio_vigencia is not None or self.data_fim_vigencia is not None:
            raise ValueError(f"Instrumentos do tipo '{self.tipo.value}' não têm datas de vigência.")


class InstrumentoSubStatusAtualizar(BaseModel):
    sub_status: SubStatusInstrumento


class InstrumentoProcessualSaida(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    tipo: TipoInstrumento
    modelo_ripm_id: uuid.UUID
    fundamentacao_lei: FundamentacaoLei
    fundamentacao_artigo: str
    sub_status: SubStatusInstrumento
    numero_documento_sei: str | None
    data_inicio_vigencia: date | None
    data_fim_vigencia: date | None
    valor_delta: Decimal | None
    observacoes: str | None

    model_config = {"from_attributes": True}
