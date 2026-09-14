import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.contrato import (
    ExcecaoTetoVigencia,
    FormaContratacao,
    ModoExecucao,
    SistemaProcesso,
    StatusContrato,
    TipoProcesso,
    TipoReajuste,
)
from app.models.instrumento_processual import FundamentacaoLei
from app.schemas.fiscal import FiscalVinculoSaida
from app.schemas.instrumento import InstrumentoProcessualSaida


class ProcessoCriar(BaseModel):
    numero_processo: str = Field(..., max_length=50)
    sistema_origem: SistemaProcesso
    tipo: TipoProcesso


class ProcessoAtualizar(BaseModel):
    numero_processo: str | None = Field(None, max_length=50)
    sistema_origem: SistemaProcesso | None = None
    tipo: TipoProcesso | None = None


class ProcessoSaida(BaseModel):
    id: uuid.UUID
    numero_processo: str
    sistema_origem: SistemaProcesso
    tipo: TipoProcesso
    criado_em: datetime

    model_config = {"from_attributes": True}


class InstrumentoOrigemCriar(BaseModel):
    """O instrumento de Origem — primeiro prazo de vigência do contrato,
    criado junto com o contrato (não depois, como os aditivos). O RIPM aqui é
    só o checklist de apoio administrativo (não é documento jurídico do
    processo como o próprio instrumento), por isso é opcional; a
    fundamentação legal (lei + artigo) é a mesma exigida de qualquer
    instrumento que define vigência (seção 4.2)."""

    modelo_ripm_id: uuid.UUID | None = None
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
    tipo_servico: str = Field(..., max_length=200)
    objeto: str = Field(..., min_length=3)
    fornecedor_id: uuid.UUID
    forma_contratacao: FormaContratacao
    data_assinatura_original: date
    valor_inicial: Decimal = Field(..., gt=0)
    # Contratos antigos que estão entrando no sistema agora, não vale a pena
    # lançar fatura por fatura do que já foi pago — lança-se esse total de
    # uma vez aqui, e o faturamento (módulo Faturamento) passa a valer só
    # daqui para frente. Em contrato genuinamente novo, fica 0 (padrão).
    valor_pago_anterior_sistema: Decimal = Field(Decimal("0"), ge=0)
    nota_reserva: str | None = None
    nota_empenho: str | None = None
    pt: str | None = None
    nd: str | None = None
    fr: str | None = None
    tipo_patrimonial: str | None = None
    item_patrimonial: str | None = None
    codigo_ccon: str | None = None
    observacoes: str | None = None
    # Exceção ao teto de 5 anos (art. 71, I ou II, da Lei 13.303/16) — nula na
    # imensa maioria dos contratos. Marcada, exige justificativa e o número do
    # documento (parecer jurídico/SEI) que a formaliza — ex.: locação de
    # imóvel, cujo prazo longo é prática rotineira de mercado (inciso II).
    excecao_teto_vigencia: ExcecaoTetoVigencia | None = None
    excecao_teto_justificativa: str | None = Field(None, max_length=2000)
    excecao_teto_documento_sei: str | None = Field(None, max_length=50)
    # Nem todo contrato é faturado pela Gerência de Contratos (ex.: benefícios
    # são faturados pelo RH, jurídicos pela AJU). Quando falso, este contrato
    # não entra no módulo de Faturamento — a GCT só gerencia prazo/renovação.
    faturamento_gerido_pela_gct: bool = True
    setor_responsavel_faturamento: str | None = Field(None, max_length=100)
    # Reajuste — nulo quando o contrato não tem cláusula de reajuste (ex.:
    # compra pontual, licença de software sem previsão de correção).
    # `tipo_reajuste` distingue cláusula obrigatória (a Rio-Urbe aplica assim
    # que completa o prazo, sem precisar de pedido) de reajuste que só ocorre
    # se a contratada solicitar. A periodicidade não é fixa em 24 meses no
    # sistema — cada contrato traz a sua na própria cláusula.
    tipo_reajuste: TipoReajuste | None = None
    periodicidade_reajuste_meses: int | None = Field(None, ge=1, le=120)
    indice_reajuste_padrao: str | None = Field(None, max_length=50)
    # Controle por vigência (padrão) ou por quantidade de execuções (ex.:
    # limpeza de carpete, aplicada N vezes por exercício) — ver ModoExecucao.
    # A vigência continua sendo informada (instrumento_origem) mesmo em
    # modo por_quantidade: ela ainda limita o exercício, só não é o critério
    # de conclusão do contrato.
    modo_execucao: ModoExecucao = ModoExecucao.POR_VIGENCIA
    quantidade_execucoes_previstas: int | None = Field(None, ge=1, le=1000)

    @model_validator(mode="after")
    def _excecao_exige_justificativa_e_documento(self):
        if self.excecao_teto_vigencia is not None and (
            not self.excecao_teto_justificativa or not self.excecao_teto_documento_sei
        ):
            raise ValueError(
                "Marcar exceção ao teto de 5 anos exige justificativa e o número do "
                "documento (parecer jurídico/SEI) que a formaliza."
            )
        return self

    @model_validator(mode="after")
    def _setor_responsavel_quando_nao_e_gct(self):
        if not self.faturamento_gerido_pela_gct and not (self.setor_responsavel_faturamento or "").strip():
            raise ValueError(
                "Informe o setor responsável pelo faturamento quando ele não é feito pela "
                "Gerência de Contratos."
            )
        return self

    @model_validator(mode="after")
    def _periodicidade_exige_tipo_reajuste(self):
        if self.tipo_reajuste is not None and self.periodicidade_reajuste_meses is None:
            raise ValueError("Informe a periodicidade do reajuste (em meses) quando o contrato tem cláusula de reajuste.")
        return self

    @model_validator(mode="after")
    def _quantidade_execucoes_condiz_com_modo(self):
        if self.modo_execucao == ModoExecucao.POR_QUANTIDADE and self.quantidade_execucoes_previstas is None:
            raise ValueError(
                "Informe a quantidade de execuções previstas quando o contrato é controlado por quantidade."
            )
        if self.modo_execucao == ModoExecucao.POR_VIGENCIA and self.quantidade_execucoes_previstas is not None:
            raise ValueError("Quantidade de execuções previstas só se aplica a contrato controlado por quantidade.")
        return self

    # Prazo de vigência inicial (Relógio 1) — o teto de 5 anos (Relógio 2) só
    # funciona corretamente se o contrato já nascer com esse marco zero;
    # prorrogações depois entram como novos instrumentos na ficha do contrato.
    instrumento_origem: InstrumentoOrigemCriar
    # Número(s) de processo — sempre pelo menos 1 (histórico entre os 3
    # sistemas já usados: SICOP físico, Processo.Rio, SEI.Rio, e/ou apensos
    # ao processo principal).
    processos: list[ProcessoCriar] = Field(..., min_length=1)
    # Fiscal obrigatório — gap identificado na planilha antiga (seção 4.5).
    # Vínculo(s) inicial(is); data_inicio de cada um é a data de assinatura
    # original por padrão do lado do frontend, mas pode ser ajustada.
    fiscais_ids: list[uuid.UUID] = Field(..., min_length=1)


class ContratoAtualizar(BaseModel):
    """Edição geral do contrato — todos os campos opcionais (só atualiza o
    que for enviado). Não inclui `status` (só muda via instrumento
    processual, seção 4.3) nem `fiscais`/`processos` (têm endpoints
    próprios, já que são coleções, não um campo simples do contrato)."""

    numero_contrato: str | None = Field(None, max_length=50)
    tipo_servico: str | None = Field(None, max_length=200)
    objeto: str | None = Field(None, min_length=3)
    fornecedor_id: uuid.UUID | None = None
    forma_contratacao: FormaContratacao | None = None
    data_assinatura_original: date | None = None
    valor_inicial: Decimal | None = Field(None, gt=0)
    # valor_pago não é editável aqui — ele é sempre calculado (nunca digitado
    # direto), soma de valor_pago_anterior_sistema com o que as faturas pagas
    # no sistema cobrem. Ajuste pelo endpoint dedicado `/pagamento`.
    nota_reserva: str | None = None
    nota_empenho: str | None = None
    pt: str | None = None
    nd: str | None = None
    fr: str | None = None
    tipo_patrimonial: str | None = None
    item_patrimonial: str | None = None
    codigo_ccon: str | None = None
    observacoes: str | None = None
    # Mesma exceção ao teto de 5 anos de ContratoCriar — pode ser marcada
    # depois da criação (ex.: uma prorrogação revela que o caso se enquadra),
    # ou desmarcada (envie null para os 3 campos, e a rota também limpa
    # justificativa/documento nesse caso, mesmo que não reenviados).
    excecao_teto_vigencia: ExcecaoTetoVigencia | None = None
    excecao_teto_justificativa: str | None = Field(None, max_length=2000)
    excecao_teto_documento_sei: str | None = Field(None, max_length=50)
    # Mesma regra de setor responsável de ContratoCriar — envie
    # faturamento_gerido_pela_gct=true para devolver o faturamento à GCT (a
    # rota também limpa setor_responsavel_faturamento nesse caso).
    faturamento_gerido_pela_gct: bool | None = None
    setor_responsavel_faturamento: str | None = Field(None, max_length=100)
    # Mesma classificação de reajuste de ContratoCriar — envie
    # tipo_reajuste=null para remover a cláusula (a rota também limpa
    # periodicidade e índice padrão nesse caso).
    tipo_reajuste: TipoReajuste | None = None
    periodicidade_reajuste_meses: int | None = Field(None, ge=1, le=120)
    indice_reajuste_padrao: str | None = Field(None, max_length=50)
    # Mesma classificação de ContratoCriar — pode ser ajustada depois da
    # criação (ex.: percebeu-se que o contrato se enquadra no modelo por
    # quantidade só depois de cadastrado).
    modo_execucao: ModoExecucao | None = None
    quantidade_execucoes_previstas: int | None = Field(None, ge=1, le=1000)

    @model_validator(mode="after")
    def _excecao_exige_justificativa_e_documento(self):
        if self.excecao_teto_vigencia is not None and (
            not self.excecao_teto_justificativa or not self.excecao_teto_documento_sei
        ):
            raise ValueError(
                "Marcar exceção ao teto de 5 anos exige justificativa e o número do "
                "documento (parecer jurídico/SEI) que a formaliza."
            )
        return self

    @model_validator(mode="after")
    def _setor_responsavel_quando_nao_e_gct(self):
        if self.faturamento_gerido_pela_gct is False and not (self.setor_responsavel_faturamento or "").strip():
            raise ValueError(
                "Informe o setor responsável pelo faturamento quando ele não é feito pela "
                "Gerência de Contratos."
            )
        return self

    @model_validator(mode="after")
    def _periodicidade_exige_tipo_reajuste(self):
        if self.tipo_reajuste is not None and self.periodicidade_reajuste_meses is None:
            raise ValueError("Informe a periodicidade do reajuste (em meses) quando o contrato tem cláusula de reajuste.")
        return self

    @model_validator(mode="after")
    def _quantidade_execucoes_condiz_com_modo(self):
        if self.modo_execucao == ModoExecucao.POR_QUANTIDADE and self.quantidade_execucoes_previstas is None:
            raise ValueError(
                "Informe a quantidade de execuções previstas quando o contrato é controlado por quantidade."
            )
        if self.modo_execucao == ModoExecucao.POR_VIGENCIA and self.quantidade_execucoes_previstas is not None:
            raise ValueError("Quantidade de execuções previstas só se aplica a contrato controlado por quantidade.")
        return self


class ExecucaoCriar(BaseModel):
    """Registra uma execução do serviço, para contrato controlado por
    quantidade — cada aplicação é uma linha nova, nunca editada depois
    (mesmo princípio do histórico de garantia)."""

    data_execucao: date
    observacao: str | None = Field(None, max_length=500)


class ExecucaoSaida(BaseModel):
    id: uuid.UUID
    data_execucao: date
    observacao: str | None
    registrado_por_nome: str
    registrado_em: datetime

    model_config = {"from_attributes": True}


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


class TempoRestanteSaida(BaseModel):
    """Contagem regressiva da vigência — quando `vencido`, conta o tempo
    decorrido desde o vencimento."""

    vencido: bool
    dias_totais: int
    meses: int
    dias: int

    # O serviço devolve um dataclass; sem isto o Pydantic recusa o objeto.
    model_config = {"from_attributes": True}


class CalculoVigenciaSaida(BaseModel):
    """Resposta do contador de datas: informado o início e o prazo em meses,
    devolve o fim da vigência e se isso estoura o teto de 5 anos."""

    data_inicio: date
    meses: int
    data_fim: date
    teto_cinco_anos: date | None = None
    excede_teto: bool = False


class LinhaReajusteSaida(BaseModel):
    """Uma competência (mês) da distribuição do apostilamento."""

    competencia: date
    valor_antigo: Decimal
    valor_reajustado: Decimal
    diferenca: Decimal

    model_config = {"from_attributes": True}


class CalculoReajusteSaida(BaseModel):
    """Resposta da calculadora de reajuste: valor mensal reajustado e a
    distribuição mês a mês do que o apostilamento formaliza — substitui a
    calculadora do cidadão para a parte de conta (o índice em si continua
    sendo informado por quem calcula)."""

    valor_mensal_antigo: Decimal
    valor_mensal_novo: Decimal
    percentual_variacao: Decimal
    linhas: list[LinhaReajusteSaida]
    valor_total_apostilamento: Decimal

    model_config = {"from_attributes": True}


class LogAuditoriaSaida(BaseModel):
    id: uuid.UUID
    acao: str
    usuario_nome: str | None
    detalhes: dict | None
    criado_em: datetime

    model_config = {"from_attributes": True}


class ContratoAtualizarPagamento(BaseModel):
    """Ajusta só a parte manual do valor pago — o que foi pago fora do
    controle de faturas deste sistema (histórico anterior à entrada do
    contrato no sistema, ou o total de um contrato cujo faturamento é de
    outro setor). O valor pago total exibido soma isto com o que as faturas
    pagas no sistema já cobrem — nunca substitui, sempre soma."""

    valor_pago_anterior_sistema: Decimal = Field(..., ge=0)


class ContratoSaida(BaseModel):
    id: uuid.UUID
    numero_contrato: str
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
    processos: list[ProcessoSaida]
    # Incluídos aqui (não só em ContratoDetalhado) para aparecer já na
    # listagem/dashboard — contratos perto de vencer vigência ou garantia
    # precisam ser visíveis no Kanban, não só na ficha do contrato.
    alerta_vigencia: str | None
    alerta_garantia: str | None
    alerta_reajuste: str | None
    # Também na listagem — a tela de Nova fatura precisa saber quais
    # contratos aceitam fatura sem abrir cada um; o Kanban usa para o selo.
    faturamento_gerido_pela_gct: bool
    setor_responsavel_faturamento: str | None

    model_config = {"from_attributes": True}


class ContratoDetalhado(ContratoSaida):
    fiscais: list[FiscalVinculoSaida]
    valor_atualizado: Decimal
    saldo_a_pagar: Decimal
    # Parte manual do valor pago (ver ContratoAtualizarPagamento) — a tela de
    # edição pré-carrega o box de ajuste a partir daqui, não de valor_pago
    # (que já inclui as faturas pagas no sistema).
    valor_pago_anterior_sistema: Decimal
    vigencia_inicio: date | None
    vigencia_fim: date | None
    # Nulo quando o contrato tem exceção registrada (excecao_teto_vigencia) —
    # a lei remove o teto nesses casos, não impõe um novo.
    teto_vigencia: date | None
    excecao_teto_vigencia: ExcecaoTetoVigencia | None
    excecao_teto_justificativa: str | None
    excecao_teto_documento_sei: str | None
    # Contagem regressiva até o fim da vigência atual (ou o tempo decorrido,
    # se já venceu). Nula enquanto não houver instrumento de origem.
    tempo_restante_vigencia: TempoRestanteSaida | None = None
    garantia_inicio: date | None
    garantia_fim: date | None
    garantias: list[GarantiaSaida]
    # Reajuste — nulo quando o contrato não tem cláusula de reajuste.
    tipo_reajuste: TipoReajuste | None
    periodicidade_reajuste_meses: int | None
    indice_reajuste_padrao: str | None
    proximo_marco_reajuste: date | None = None
    # Controle por quantidade de execuções (ex.: limpeza de carpete) — vazio/
    # falso na imensa maioria dos contratos, que usa vigência normalmente.
    modo_execucao: ModoExecucao
    quantidade_execucoes_previstas: int | None
    quantidade_execucoes_atingida: bool = False
    execucoes: list[ExecucaoSaida]
    instrumentos: list[InstrumentoProcessualSaida]
