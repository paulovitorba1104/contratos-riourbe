import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fiscal import Fiscal
    from app.models.fornecedor import Fornecedor
    from app.models.instrumento_processual import InstrumentoProcessual
    from app.models.usuario import Usuario


class FormaContratacao(str, enum.Enum):
    PREGAO_ELETRONICO = "pregao_eletronico"
    DISPENSA = "dispensa"
    INEXIGIBILIDADE = "inexigibilidade"


class StatusContrato(str, enum.Enum):
    VIGENTE = "vigente"
    SUSPENSO = "suspenso"
    ENCERRADO = "encerrado"


class ExcecaoTetoVigencia(str, enum.Enum):
    """As duas exceções ao teto de 5 anos do art. 71 da Lei 13.303/16 — sem
    elas, `teto_vigencia` sempre bloqueia prorrogação além de 5 anos da
    assinatura original. Marcar aqui remove o teto para este contrato (não o
    estende para um novo número de anos: a lei simplesmente não impõe limite
    nesses dois casos)."""

    ART_71_I = "art_71_i"  # projeto contemplado no plano de negócios e investimentos da empresa
    ART_71_II = "art_71_ii"  # prazo maior é prática rotineira de mercado (ex.: locação de imóvel)


class ModoExecucao(str, enum.Enum):
    """A maioria dos contratos executa continuamente dentro de um período de
    vigência (datas) — Relógio 1 de sempre. Alguns não seguem essa lógica:
    dispensa de licitação com execução sazonal (ex.: limpeza de carpete,
    aplicada N vezes dentro do mesmo exercício) não tem prazo em dias, tem
    uma quantidade prevista de execuções no termo de referência. Nesses
    contratos normalmente também não há assinatura de contrato/termo
    aditivo — `data_assinatura_original` passa a ser a data de publicação no
    Diário Oficial (mesmo campo, rótulo diferente na tela)."""

    POR_VIGENCIA = "por_vigencia"
    POR_QUANTIDADE = "por_quantidade"


class ModoValorContrato(str, enum.Enum):
    """A maioria dos contratos já nasce com o valor total (global) definido —
    é o que se digita em `valor_inicial`. Alguns (ex.: locação de imóvel) são
    cotados por mensalidade — o valor global é derivado (mensal × meses
    cobrados, descontada a carência), não digitado direto."""

    GLOBAL = "global"
    MENSAL = "mensal"


class TipoReajuste(str, enum.Enum):
    """Nem todo contrato reajusta do mesmo jeito: alguns têm cláusula que
    obriga o reajuste (a Rio-Urbe aplica assim que o prazo se completa,
    independente de pedido); outros só reajustam se a contratada pedir —
    sem pedido, o preço simplesmente fica parado, mesmo com o índice
    variando. Nulo = contrato sem cláusula de reajuste (ex.: compra pontual,
    licença de software sem previsão de correção)."""

    AUTOMATICO = "automatico"
    MEDIANTE_SOLICITACAO = "mediante_solicitacao"


class SistemaProcesso(str, enum.Enum):
    """Sistema onde o número do processo foi aberto — a Prefeitura já passou
    por 3 sistemas de processo administrativo."""

    SICOP = "sicop"
    PROCESSO_RIO = "processo_rio"
    SEI_RIO = "sei_rio"


class TipoProcesso(str, enum.Enum):
    PRINCIPAL = "principal"
    APENSO = "apenso"


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
    numero_contrato: Mapped[str] = mapped_column(String(50), nullable=False)
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
    # Exceção ao teto de 5 anos (art. 71, I ou II, da Lei 13.303/16) — nula na
    # imensa maioria dos contratos. Quando marcada, exige justificativa e o
    # documento que a formaliza (schema valida isso, não o banco).
    excecao_teto_vigencia: Mapped[ExcecaoTetoVigencia | None] = mapped_column(
        Enum(
            ExcecaoTetoVigencia,
            name="excecao_teto_vigencia",
            schema="contratos",
            values_callable=_valores_enum,
        ),
        nullable=True,
    )
    excecao_teto_justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    excecao_teto_documento_sei: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Controle por vigência (padrão) ou por quantidade de execuções — ver
    # ModoExecucao. Nula-equivalente é por_vigencia (imensa maioria).
    modo_execucao: Mapped[ModoExecucao] = mapped_column(
        Enum(ModoExecucao, name="modo_execucao", schema="contratos", values_callable=_valores_enum),
        nullable=False,
        default=ModoExecucao.POR_VIGENCIA,
    )
    # Só preenchida quando modo_execucao = por_quantidade — quantas vezes o
    # serviço está previsto para ser executado (ex.: 3x/ano).
    quantidade_execucoes_previstas: Mapped[int | None] = mapped_column(nullable=True)

    # Nem todo contrato é faturado pela Gerência de Contratos — benefícios são
    # faturados pelo RH, jurídicos pela AJU, por exemplo. Quando falso, este
    # contrato não entra no módulo de Faturamento: a GCT só gerencia prazo e
    # renovação dele, o faturamento é responsabilidade de outro setor.
    faturamento_gerido_pela_gct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    setor_responsavel_faturamento: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Financeiro
    # Valor total do contrato — sempre a fonte de verdade usada em
    # calcular_valor_atualizado/saldo_a_pagar, mesmo quando modo_valor é
    # mensal: nesse caso o backend calcula e grava aqui (nunca confia num
    # valor_inicial mandado pelo cliente para esse modo).
    valor_inicial: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    # Contrato cotado por mensalidade (ex.: locação de imóvel) em vez de
    # valor global direto — valor_mensal e carencia_meses são a base usada
    # para calcular valor_inicial (valor_mensal × (prazo - carência)).
    modo_valor: Mapped[ModoValorContrato] = mapped_column(
        Enum(ModoValorContrato, name="modo_valor_contrato", schema="contratos", values_callable=_valores_enum),
        nullable=False,
        default=ModoValorContrato.GLOBAL,
    )
    valor_mensal: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    carencia_meses: Mapped[int | None] = mapped_column(nullable=True)
    # Total pago: soma do que veio de fora do controle de faturas deste
    # sistema (valor_pago_anterior_sistema — histórico de contrato antigo, ou
    # o total de um contrato cujo faturamento é de outro setor) com o que as
    # faturas pagas aqui dentro já cobrem. Nunca editado diretamente fora
    # dessa soma — ver `atualizar_pagamento` e `_sincronizar_valor_pago`.
    valor_pago: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    # Parte manual do valor pago: o que foi pago antes deste contrato entrar
    # no controle de faturas do sistema (não vale a pena lançar retroativo
    # fatura por fatura de um contrato antigo — lança-se esse total de uma
    # vez e o faturamento passa a valer só daqui para frente) ou, quando
    # faturamento_gerido_pela_gct é falso, o valor total pago, atualizado à
    # mão porque nunca haverá fatura deste contrato no sistema.
    valor_pago_anterior_sistema: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    # Obras e serviços continuados medem o período executado antes de o
    # fornecedor emitir a nota; compra pontual não. Quando marcado, o módulo
    # de Faturamento só aceita fatura vinculada a uma medição aprovada.
    exige_medicao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nota_reserva: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nota_empenho: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Reajuste — nulo quando o contrato não tem cláusula de reajuste.
    tipo_reajuste: Mapped[TipoReajuste | None] = mapped_column(
        Enum(TipoReajuste, name="tipo_reajuste", schema="contratos", values_callable=_valores_enum),
        nullable=True,
    )
    # Cada contrato define seu próprio intervalo na cláusula — 24 meses é
    # comum, mas não é universal, por isso não é uma constante do sistema.
    periodicidade_reajuste_meses: Mapped[int | None] = mapped_column(nullable=True)
    # Sugestão pré-preenchida na calculadora de reajuste (seção 4.6) — o
    # índice de fato usado em cada reajuste fica registrado no instrumento
    # (pode divergir daqui se a cláusula previr substituição de índice).
    indice_reajuste_padrao: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Orçamentário/contábil
    pt: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nd: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fr: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_patrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_patrimonial: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_ccon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Número(s) de processo administrativo — um contrato pode ter mais de um
    # (histórico entre os 3 sistemas já usados: SICOP físico, Processo.Rio,
    # SEI.Rio), cada um marcado como o processo principal ou um apenso dele.
    processos: Mapped[list["ProcessoContrato"]] = relationship(
        back_populates="contrato", order_by="ProcessoContrato.criado_em", cascade="all, delete-orphan"
    )
    instrumentos: Mapped[list["InstrumentoProcessual"]] = relationship(
        back_populates="contrato", order_by="InstrumentoProcessual.criado_em", cascade="all, delete-orphan"
    )
    fiscais: Mapped[list["ContratoFiscal"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )
    # Relógio 3: garantia contratual — independente da vigência. Cada
    # alteração gera um novo registro (nunca sobrescreve o anterior), então
    # fica auditável quem mudou o quê e quando — o mesmo princípio já usado
    # para vigência via instrumentos processuais.
    garantias: Mapped[list["GarantiaContrato"]] = relationship(
        back_populates="contrato", order_by="GarantiaContrato.registrado_em", cascade="all, delete-orphan"
    )
    # Histórico de execuções — só usado quando modo_execucao = por_quantidade
    # (fica vazio para a imensa maioria dos contratos, que usa vigência).
    execucoes: Mapped[list["ExecucaoContrato"]] = relationship(
        back_populates="contrato", order_by="ExecucaoContrato.data_execucao", cascade="all, delete-orphan"
    )
    # Fornecedores além do principal (fornecedor_id) — caso da locação de
    # imóvel em que uma empresa recebe o aluguel e outra administra o
    # condomínio (IPTU, taxa condominial, água/luz etc.), tudo dentro do
    # mesmo contrato. Vazio na imensa maioria dos contratos (um fornecedor só).
    fornecedores_adicionais: Mapped[list["FornecedorAdicionalContrato"]] = relationship(
        back_populates="contrato", order_by="FornecedorAdicionalContrato.criado_em", cascade="all, delete-orphan"
    )


class FornecedorAdicionalContrato(Base):
    """Fornecedor adicional vinculado ao contrato, além do principal
    (`Contrato.fornecedor_id`) — cada um com um papel (ex.: "Administradora
    do condomínio"). Uma fatura pode ser emitida para qualquer um dos
    fornecedores do contrato (o principal ou um destes), nunca para fora
    desse conjunto — ver `Fatura.fornecedor_id`."""

    __tablename__ = "fornecedores_adicionais_contrato"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.fornecedores.id"), nullable=False)
    papel: Mapped[str] = mapped_column(String(100), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contrato: Mapped["Contrato"] = relationship(back_populates="fornecedores_adicionais")
    fornecedor: Mapped["Fornecedor"] = relationship()


class ContratoFiscal(Base):
    """Vínculo de fiscalização — fiscal(is) do contrato, obrigatório (gap
    identificado na planilha antiga). É um vínculo temporal, não uma simples
    associação: um fiscal pode entrar e sair da fiscalização ao longo da
    vida do contrato (substituição), então cada linha tem início e,
    opcionalmente, fim de vigência. `data_fim` nula = vínculo ainda ativo.
    """

    __tablename__ = "contrato_fiscais"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    fiscal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.fiscais.id"), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship(back_populates="fiscais")
    fiscal: Mapped["Fiscal"] = relationship()


class GarantiaContrato(Base):
    """Registro histórico de garantia contratual (Relógio 3). Cada alteração
    (definição inicial ou correção) cria uma nova linha em vez de sobrescrever
    a anterior — a garantia "atual" é sempre a mais recentemente registrada,
    igual ao princípio de vigência via instrumentos processuais, mas aqui sem
    RIPM/fundamentação legal por não ser um instrumento processual formal."""

    __tablename__ = "garantias_contrato"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    data_inicio_garantia: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_garantia: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    registrado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contrato: Mapped["Contrato"] = relationship(back_populates="garantias")
    registrado_por: Mapped["Usuario"] = relationship()


class ExecucaoContrato(Base):
    """Registro de uma execução do serviço, para contrato controlado por
    quantidade (modo_execucao = por_quantidade), não por vigência de datas —
    ex.: limpeza de carpete aplicada N vezes no ano. Cada aplicação é uma
    linha nova, nunca editada depois de registrada (mesmo princípio do
    histórico de garantia) — a quantidade realizada é sempre `len(execucoes)`."""

    __tablename__ = "execucoes_contrato"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    data_execucao: Mapped[date] = mapped_column(Date, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    registrado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.usuarios.id"), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contrato: Mapped["Contrato"] = relationship(back_populates="execucoes")
    registrado_por: Mapped["Usuario"] = relationship()


class ProcessoContrato(Base):
    """Número de processo administrativo vinculado ao contrato. Um contrato
    pode ter mais de um: histórico entre os 3 sistemas já usados (SICOP
    físico, Processo.Rio, SEI.Rio) e/ou processos apensos ao principal."""

    __tablename__ = "processos_contrato"
    __table_args__ = {"schema": "contratos"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contratos.contratos.id", ondelete="CASCADE"), nullable=False
    )
    numero_processo: Mapped[str] = mapped_column(String(50), nullable=False)
    sistema_origem: Mapped[SistemaProcesso] = mapped_column(
        Enum(SistemaProcesso, name="sistema_processo", schema="contratos", values_callable=_valores_enum),
        nullable=False,
    )
    tipo: Mapped[TipoProcesso] = mapped_column(
        Enum(TipoProcesso, name="tipo_processo", schema="contratos", values_callable=_valores_enum),
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contrato: Mapped["Contrato"] = relationship(back_populates="processos")
