import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.instrumento_processual import (
    TIPOS_QUE_DEFINEM_VIGENCIA,
    FundamentacaoLei,
    SubStatusInstrumento,
    TipoInstrumento,
)

# Os 6 campos de reajuste do apostilamento — ou vêm todos, ou nenhum (ver
# _valida_campos_por_tipo). reajuste_valor_mensal_novo não está aqui de
# propósito: quem calcula é o backend (app/services/reajuste.py), nunca o
# cliente — mesmo racional do valor_delta, que também é calculado, não digitado.
_CAMPOS_REAJUSTE = (
    "reajuste_indice_nome",
    "reajuste_indice_atual",
    "reajuste_indice_base",
    "reajuste_valor_mensal_antigo",
    "reajuste_data_inicio",
    "reajuste_data_fim",
)


class InstrumentoProcessualCriar(BaseModel):
    tipo: TipoInstrumento
    # RIPM é só um checklist de apoio administrativo (não documento jurídico
    # do processo) — opcional.
    modelo_ripm_id: uuid.UUID | None = None
    fundamentacao_lei: FundamentacaoLei
    fundamentacao_artigo: str = Field(..., max_length=100)
    numero_documento_sei: str | None = Field(None, max_length=50)
    data_inicio_vigencia: date | None = None
    data_fim_vigencia: date | None = None
    valor_delta: Decimal | None = None
    # Reajuste (só para tipo=apostilamento) — informe os 6 campos abaixo para
    # o backend calcular o valor mensal novo e o valor_delta (soma das
    # diferenças mensais) sozinho; veja GET /contratos/calcular-reajuste para
    # pré-visualizar antes de enviar.
    reajuste_indice_nome: str | None = Field(None, max_length=50)
    reajuste_indice_atual: Decimal | None = None
    reajuste_indice_base: Decimal | None = None
    reajuste_valor_mensal_antigo: Decimal | None = None
    reajuste_data_inicio: date | None = None
    reajuste_data_fim: date | None = None
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
            self._exige_sem_reajuste()
        elif self.tipo == TipoInstrumento.ACRESCIMO_VALOR:
            if self.valor_delta is None or self.valor_delta <= 0:
                raise ValueError("Acréscimo de valor exige valor_delta positivo.")
            self._exige_sem_vigencia()
            self._exige_sem_reajuste()
        elif self.tipo == TipoInstrumento.SUPRESSAO_VALOR:
            if self.valor_delta is None or self.valor_delta >= 0:
                raise ValueError("Supressão de valor exige valor_delta negativo.")
            self._exige_sem_vigencia()
            self._exige_sem_reajuste()
        elif self.tipo == TipoInstrumento.APOSTILAMENTO:
            self._exige_sem_vigencia()
            self._valida_reajuste()
        else:
            if self.valor_delta is not None:
                raise ValueError(f"Instrumentos do tipo '{self.tipo.value}' não têm valor_delta.")
            self._exige_sem_vigencia()
            self._exige_sem_reajuste()
        return self

    def _exige_sem_vigencia(self) -> None:
        if self.data_inicio_vigencia is not None or self.data_fim_vigencia is not None:
            raise ValueError(f"Instrumentos do tipo '{self.tipo.value}' não têm datas de vigência.")

    def _exige_sem_reajuste(self) -> None:
        if any(getattr(self, campo) is not None for campo in _CAMPOS_REAJUSTE):
            raise ValueError(f"Instrumentos do tipo '{self.tipo.value}' não têm cálculo de reajuste.")

    def _valida_reajuste(self) -> None:
        """Apostilamento comum: valor_delta livre (opcional, qualquer sinal),
        sem campos de reajuste. Apostilamento de reajuste: todos os 6 campos
        de reajuste, e o próprio backend calcula o valor_delta — não aceita
        os dois ao mesmo tempo."""
        preenchidos = [getattr(self, campo) is not None for campo in _CAMPOS_REAJUSTE]
        if not any(preenchidos):
            return
        if not all(preenchidos):
            raise ValueError(
                "Para calcular o reajuste, informe índice atual, índice base, valor mensal "
                "antigo, nome do índice e o período (início e fim) completos."
            )
        if self.valor_delta is not None:
            raise ValueError(
                "O valor do apostilamento de reajuste é calculado pelo sistema — não envie valor_delta."
            )
        if self.reajuste_data_fim <= self.reajuste_data_inicio:
            raise ValueError("A data final do reajuste deve ser posterior à data inicial.")


class InstrumentoSubStatusAtualizar(BaseModel):
    sub_status: SubStatusInstrumento


class AnexoInstrumentoSaida(BaseModel):
    id: uuid.UUID
    nome_arquivo: str
    tipo_mime: str
    tamanho_bytes: int
    enviado_por_nome: str
    enviado_em: datetime

    model_config = {"from_attributes": True}


class InstrumentoProcessualSaida(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    tipo: TipoInstrumento
    modelo_ripm_id: uuid.UUID | None
    fundamentacao_lei: FundamentacaoLei
    fundamentacao_artigo: str
    sub_status: SubStatusInstrumento
    numero_documento_sei: str | None
    data_inicio_vigencia: date | None
    data_fim_vigencia: date | None
    valor_delta: Decimal | None
    reajuste_indice_nome: str | None = None
    reajuste_indice_atual: Decimal | None = None
    reajuste_indice_base: Decimal | None = None
    reajuste_valor_mensal_antigo: Decimal | None = None
    reajuste_valor_mensal_novo: Decimal | None = None
    reajuste_data_inicio: date | None = None
    reajuste_data_fim: date | None = None
    observacoes: str | None
    anexos: list[AnexoInstrumentoSaida] = []

    model_config = {"from_attributes": True}
