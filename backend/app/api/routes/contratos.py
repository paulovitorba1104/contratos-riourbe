import uuid
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.contrato import (
    Contrato,
    ContratoFiscal,
    ExcecaoTetoVigencia,
    ExecucaoContrato,
    FornecedorAdicionalContrato,
    GarantiaContrato,
    ModoExecucao,
    ModoValorContrato,
    ProcessoContrato,
    StatusContrato,
)
from app.models.fiscal import Fiscal
from app.models.fornecedor import Fornecedor
from app.models.faturamento import Fatura
from app.models.instrumento_processual import AnexoInstrumento, InstrumentoProcessual, TipoInstrumento
from app.models.log_auditoria import LogAuditoria
from app.models.modelo_ripm import ModeloRipm
from app.models.usuario import Usuario
from app.schemas.contrato import (
    CalculoReajusteSaida,
    CalculoValorMensalSaida,
    CalculoVigenciaSaida,
    ContratoAtualizar,
    ContratoAtualizarPagamento,
    ContratoCriar,
    ContratoDetalhado,
    ContratoSaida,
    ExecucaoCriar,
    ExecucaoSaida,
    FornecedorAdicionalCriar,
    FornecedorAdicionalSaida,
    GarantiaCriar,
    GarantiaSaida,
    LinhaReajusteSaida,
    LogAuditoriaSaida,
    ProcessoAtualizar,
    ProcessoCriar,
)
from app.schemas.fiscal import FiscalEncerrarVinculo, FiscalVincular, FiscalVinculoSaida
from app.schemas.instrumento import (
    AnexoInstrumentoSaida,
    InstrumentoProcessualCriar,
    InstrumentoProcessualSaida,
    InstrumentoSubStatusAtualizar,
)
from app.services import armazenamento
from app.services import contratos as regras
from app.services import faturamento as regras_faturamento
from app.services import reajuste as regras_reajuste
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/contratos", tags=["contratos"])


def _carregar_contrato(db: Session, contrato_id: uuid.UUID) -> Contrato:
    contrato = (
        db.query(Contrato)
        .options(
            selectinload(Contrato.instrumentos).selectinload(InstrumentoProcessual.anexos).selectinload(
                AnexoInstrumento.enviado_por
            ),
            selectinload(Contrato.fiscais).selectinload(ContratoFiscal.fiscal),
            selectinload(Contrato.garantias).selectinload(GarantiaContrato.registrado_por),
            selectinload(Contrato.execucoes).selectinload(ExecucaoContrato.registrado_por),
            selectinload(Contrato.fornecedores_adicionais).selectinload(FornecedorAdicionalContrato.fornecedor),
            selectinload(Contrato.processos),
        )
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado.")
    return contrato


def _para_saida(contrato: Contrato) -> ContratoSaida:
    alertas = regras.calcular_alertas(contrato)
    return ContratoSaida(
        **{
            campo: getattr(contrato, campo)
            for campo in ContratoSaida.model_fields
            if campo not in {"alerta_vigencia", "alerta_garantia", "alerta_reajuste"}
        },
        alerta_vigencia=alertas.alerta_vigencia,
        alerta_garantia=alertas.alerta_garantia,
        alerta_reajuste=alertas.alerta_reajuste,
    )


def _instrumento_para_saida(instrumento: InstrumentoProcessual) -> InstrumentoProcessualSaida:
    """Constrói explicitamente (em vez de deixar o Pydantic coagir sozinho)
    porque `anexos` precisa do nome de quem enviou, que não é um atributo
    direto do modelo — está em `anexo.enviado_por.nome`."""
    dados = {campo: getattr(instrumento, campo) for campo in InstrumentoProcessualSaida.model_fields if campo != "anexos"}
    return InstrumentoProcessualSaida(
        **dados,
        anexos=[
            AnexoInstrumentoSaida(
                id=anexo.id,
                nome_arquivo=anexo.nome_arquivo,
                tipo_mime=anexo.tipo_mime,
                tamanho_bytes=anexo.tamanho_bytes,
                enviado_por_nome=anexo.enviado_por.nome,
                enviado_em=anexo.enviado_em,
            )
            for anexo in instrumento.anexos
        ],
    )


def _para_detalhado(contrato: Contrato) -> ContratoDetalhado:
    vigencia_inicio, vigencia_fim = regras.vigencia_atual(contrato)
    garantia_inicio, garantia_fim = regras.garantia_atual(contrato)
    return ContratoDetalhado(
        **_para_saida(contrato).model_dump(),
        fiscais=[
            FiscalVinculoSaida(
                id=vinculo.id,
                fiscal_id=vinculo.fiscal_id,
                nome=vinculo.fiscal.nome,
                matricula=vinculo.fiscal.matricula,
                data_inicio=vinculo.data_inicio,
                data_fim=vinculo.data_fim,
            )
            for vinculo in contrato.fiscais
        ],
        valor_atualizado=regras.calcular_valor_atualizado(contrato),
        saldo_a_pagar=regras.calcular_saldo_a_pagar(contrato),
        valor_pago_anterior_sistema=contrato.valor_pago_anterior_sistema,
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        teto_vigencia=regras.teto_vigencia(contrato),
        excecao_teto_vigencia=contrato.excecao_teto_vigencia,
        excecao_teto_justificativa=contrato.excecao_teto_justificativa,
        excecao_teto_documento_sei=contrato.excecao_teto_documento_sei,
        tempo_restante_vigencia=regras.tempo_restante(vigencia_fim),
        garantia_inicio=garantia_inicio,
        garantia_fim=garantia_fim,
        exige_garantia=contrato.exige_garantia,
        garantias=[
            GarantiaSaida(
                id=g.id,
                data_inicio_garantia=g.data_inicio_garantia,
                data_fim_garantia=g.data_fim_garantia,
                observacao=g.observacao,
                registrado_por_nome=g.registrado_por.nome,
                registrado_em=g.registrado_em,
            )
            for g in contrato.garantias
        ],
        tipo_reajuste=contrato.tipo_reajuste,
        periodicidade_reajuste_meses=contrato.periodicidade_reajuste_meses,
        indice_reajuste_padrao=contrato.indice_reajuste_padrao,
        proximo_marco_reajuste=regras.proximo_marco_reajuste(contrato),
        modo_execucao=contrato.modo_execucao,
        quantidade_execucoes_previstas=contrato.quantidade_execucoes_previstas,
        quantidade_execucoes_atingida=regras.quantidade_execucoes_atingida(contrato),
        execucoes=[
            ExecucaoSaida(
                id=e.id,
                data_execucao=e.data_execucao,
                observacao=e.observacao,
                registrado_por_nome=e.registrado_por.nome,
                registrado_em=e.registrado_em,
            )
            for e in contrato.execucoes
        ],
        modo_valor=contrato.modo_valor,
        valor_mensal=contrato.valor_mensal,
        carencia_meses=contrato.carencia_meses,
        fornecedores_adicionais=[
            FornecedorAdicionalSaida(
                id=fa.id,
                fornecedor_id=fa.fornecedor_id,
                razao_social=fa.fornecedor.razao_social,
                papel=fa.papel,
            )
            for fa in contrato.fornecedores_adicionais
        ],
        instrumentos=[_instrumento_para_saida(i) for i in contrato.instrumentos],
    )


@router.get("", response_model=list[ContratoSaida])
def listar_contratos(
    status_filtro: StatusContrato | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[ContratoSaida]:
    query = db.query(Contrato).options(
        selectinload(Contrato.instrumentos),
        selectinload(Contrato.garantias),
        selectinload(Contrato.processos),
    )
    if status_filtro is not None:
        query = query.filter(Contrato.status == status_filtro)
    contratos = query.order_by(Contrato.criado_em.desc()).all()
    return [_para_saida(c) for c in contratos]


@router.get("/calcular-vigencia", response_model=CalculoVigenciaSaida)
def calcular_vigencia(
    data_inicio: date,
    # Limite alto (100 anos) só para pegar erro de digitação — o limite legal
    # de verdade é o teto de 5 anos (`excede_teto`), que tem exceção própria
    # (art. 71, I ou II) para contratos como locação de imóvel de prazo longo.
    meses: int = Query(..., ge=1, le=1200),
    data_assinatura: date | None = None,
    excecao_teto_vigencia: ExcecaoTetoVigencia | None = None,
    _: Usuario = Depends(get_current_user),
) -> CalculoVigenciaSaida:
    """Contador de datas: informado o início e o prazo em meses, devolve o fim
    da vigência. O cálculo mora no backend para a tela não errar mês de 30/31
    dias nem fevereiro — 31/01 + 1 mês é 28/02, não 03/03.

    Passando também a data de assinatura, devolve o teto de 5 anos e avisa se o
    prazo informado o ultrapassa, para o aviso aparecer enquanto a pessoa
    digita em vez de só ao salvar. Se o contrato tem exceção ao teto marcada
    (art. 71, I ou II, da Lei 13.303/16 — ex.: locação de imóvel), não há
    teto a calcular nem aviso a mostrar.
    """
    data_fim = regras.calcular_fim_vigencia(data_inicio, meses)

    teto = None
    excede = False
    if data_assinatura is not None and excecao_teto_vigencia is None:
        teto = data_assinatura + relativedelta(years=5)
        excede = data_fim > teto

    return CalculoVigenciaSaida(
        data_inicio=data_inicio,
        meses=meses,
        data_fim=data_fim,
        teto_cinco_anos=teto,
        excede_teto=excede,
    )


@router.get("/calcular-reajuste", response_model=CalculoReajusteSaida)
def calcular_reajuste(
    valor_mensal_antigo: float,
    indice_atual: float,
    indice_base: float,
    data_inicio: date,
    data_fim: date,
    _: Usuario = Depends(get_current_user),
) -> CalculoReajusteSaida:
    """Calculadora de reajuste/apostilamento (seção 4.6) — substitui a
    calculadora do cidadão para a parte de conta. `data_inicio` é o marco do
    reajuste (ex.: aniversário da vigência); `data_fim` é o próximo marco ou
    o fim da vigência do contrato, o que vier primeiro. Devolve o valor
    mensal reajustado e a distribuição mês a mês do valor a formalizar por
    apostilamento — o mesmo cálculo usado ao criar o instrumento, aqui só
    para pré-visualizar antes de enviar.
    """
    try:
        distribuicao = regras_reajuste.calcular_distribuicao_reajuste(
            valor_mensal_antigo, indice_atual, indice_base, data_inicio, data_fim
        )
    except regras_reajuste.PeriodoReajusteInvalido as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return CalculoReajusteSaida(
        valor_mensal_antigo=distribuicao.valor_mensal_antigo,
        valor_mensal_novo=distribuicao.valor_mensal_novo,
        percentual_variacao=distribuicao.percentual_variacao,
        linhas=[LinhaReajusteSaida.model_validate(linha) for linha in distribuicao.linhas],
        valor_total_apostilamento=distribuicao.valor_total_apostilamento,
    )


@router.get("/calcular-valor-mensal", response_model=CalculoValorMensalSaida)
def calcular_valor_mensal(
    valor_mensal: Decimal = Query(..., gt=0),
    prazo_meses: int = Query(..., ge=1, le=1200),
    carencia_meses: int = Query(0, ge=0, le=120),
    _: Usuario = Depends(get_current_user),
) -> CalculoValorMensalSaida:
    """Calculadora de valor global a partir da mensalidade (seção sobre
    locação de imóvel) — pré-visualiza o valor a lançar em "Valor inicial"
    antes de criar/editar o contrato; o cálculo real é refeito no backend
    ao salvar, nunca confia num valor pronto do cliente."""
    meses_cobrados = max(0, prazo_meses - carencia_meses)
    return CalculoValorMensalSaida(
        valor_mensal=valor_mensal,
        prazo_meses=prazo_meses,
        carencia_meses=carencia_meses,
        meses_cobrados=meses_cobrados,
        valor_global=regras.calcular_valor_global_mensal(valor_mensal, prazo_meses, carencia_meses),
    )


@router.get("/{contrato_id}", response_model=ContratoDetalhado)
def obter_contrato(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    return _para_detalhado(contrato)


@router.post("", response_model=ContratoDetalhado, status_code=status.HTTP_201_CREATED)
def criar_contrato(
    dados: ContratoCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    if db.get(Fornecedor, dados.fornecedor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")

    fiscais_encontrados = db.query(Fiscal.id).filter(Fiscal.id.in_(dados.fiscais_ids)).all()
    if len(fiscais_encontrados) != len(set(dados.fiscais_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Um ou mais fiscais não encontrados.")

    if dados.instrumento_origem.modelo_ripm_id is not None and db.get(
        ModeloRipm, dados.instrumento_origem.modelo_ripm_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo RIPM não encontrado.")

    contrato = Contrato(
        **dados.model_dump(exclude={"fiscais_ids", "instrumento_origem", "processos"}),
    )
    # Contrato cotado por mensalidade (ex.: locação de imóvel): o valor
    # global nunca vem pronto do cliente — é sempre calculado aqui, a partir
    # do valor mensal, da carência e do prazo do instrumento de origem.
    if dados.modo_valor == ModoValorContrato.MENSAL:
        prazo_meses = regras.meses_entre(
            dados.instrumento_origem.data_inicio_vigencia, dados.instrumento_origem.data_fim_vigencia
        )
        contrato.valor_inicial = regras.calcular_valor_global_mensal(
            dados.valor_mensal, prazo_meses, dados.carencia_meses or 0
        )
    # Nenhuma fatura existe ainda para um contrato recém-criado — o valor
    # pago total começa igual à parte manual informada (0 para contrato
    # novo; o total já pago, para um contrato antigo entrando no sistema).
    contrato.valor_pago = contrato.valor_pago_anterior_sistema
    db.add(contrato)
    db.flush()

    instrumento_origem = InstrumentoProcessual(
        contrato_id=contrato.id,
        tipo=TipoInstrumento.ORIGEM,
        **dados.instrumento_origem.model_dump(),
    )
    try:
        regras.validar_instrumento(contrato, instrumento_origem)
    except regras.TetoVigenciaExcedido as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.add(instrumento_origem)

    for processo in dados.processos:
        db.add(ProcessoContrato(contrato_id=contrato.id, **processo.model_dump()))

    for fiscal_id in set(dados.fiscais_ids):
        db.add(
            ContratoFiscal(
                contrato_id=contrato.id, fiscal_id=fiscal_id, data_inicio=contrato.data_assinatura_original
            )
        )

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
    )
    db.commit()

    return _para_detalhado(_carregar_contrato(db, contrato.id))


@router.patch("/{contrato_id}", response_model=ContratoDetalhado)
def atualizar_contrato(
    contrato_id: uuid.UUID,
    dados: ContratoAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Edição geral do contrato, incluindo valores — não muda o status
    macro (só via instrumento processual) nem os fiscais (endpoints
    próprios, seção do vínculo temporal)."""
    contrato = _carregar_contrato(db, contrato_id)

    dados_informados = dados.model_dump(exclude_unset=True)
    if "fornecedor_id" in dados_informados and db.get(Fornecedor, dados_informados["fornecedor_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")

    # Desmarcar a exceção ao teto (excecao_teto_vigencia = null) limpa também a
    # justificativa e o documento — evita texto de uma exceção que não vale
    # mais ficar parado no contrato depois de o teto voltar a valer.
    if "excecao_teto_vigencia" in dados_informados and dados_informados["excecao_teto_vigencia"] is None:
        dados_informados["excecao_teto_justificativa"] = None
        dados_informados["excecao_teto_documento_sei"] = None

    # Devolver o faturamento à GCT (faturamento_gerido_pela_gct = true) limpa
    # o setor anotado — não faz sentido ficar registrado depois da mudança.
    if dados_informados.get("faturamento_gerido_pela_gct") is True:
        dados_informados["setor_responsavel_faturamento"] = None

    # Voltar para controle por vigência (modo_execucao = por_vigencia) limpa
    # a quantidade prevista — não se aplica mais nesse modo.
    if dados_informados.get("modo_execucao") == ModoExecucao.POR_VIGENCIA:
        dados_informados["quantidade_execucoes_previstas"] = None

    # Voltar para valor global (modo_valor = global) limpa a mensalidade e a
    # carência — não se aplicam mais nesse modo. O valor_inicial atual (da
    # última vez que foi calculado no modo mensal) fica como está, editável
    # direto de novo.
    if dados_informados.get("modo_valor") == ModoValorContrato.GLOBAL:
        dados_informados["valor_mensal"] = None
        dados_informados["carencia_meses"] = None

    for campo, valor in dados_informados.items():
        setattr(contrato, campo, valor)

    # Contrato cotado por mensalidade: recalcula o valor global sempre que a
    # mensalidade, a carência ou o próprio modo mudarem nesta edição — nunca
    # aceita um valor_inicial pronto do cliente para esse modo (bloqueado já
    # no schema).
    if contrato.modo_valor == ModoValorContrato.MENSAL and (
        "valor_mensal" in dados_informados
        or "carencia_meses" in dados_informados
        or "modo_valor" in dados_informados
    ):
        vigencia_inicio, vigencia_fim = regras.vigencia_atual(contrato)
        if vigencia_inicio is None or vigencia_fim is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Contrato sem vigência registrada — não é possível calcular o valor mensal.",
            )
        prazo_meses = regras.meses_entre(vigencia_inicio, vigencia_fim)
        contrato.valor_inicial = regras.calcular_valor_global_mensal(
            Decimal(str(contrato.valor_mensal)), prazo_meses, contrato.carencia_meses or 0
        )

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"campos_alterados": list(dados_informados.keys())},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_contrato(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva do contrato inteiro (cascata: instrumentos, vínculos
    # de fiscal, histórico de garantia) — a ação mais destrutiva do sistema,
    # por isso restrita a administrador.
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    contrato = db.get(Contrato, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado.")
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"numero_contrato": contrato.numero_contrato},
    )
    db.delete(contrato)
    db.commit()


@router.post(
    "/{contrato_id}/processos",
    response_model=ContratoDetalhado,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_processo(
    contrato_id: uuid.UUID,
    dados: ProcessoCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    db.add(ProcessoContrato(contrato_id=contrato.id, **dados.model_dump()))
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="adicionar_processo_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"numero_processo": dados.numero_processo, "tipo": dados.tipo.value},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.patch(
    "/{contrato_id}/processos/{processo_id}",
    response_model=ContratoDetalhado,
)
def atualizar_processo(
    contrato_id: uuid.UUID,
    processo_id: uuid.UUID,
    dados: ProcessoAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    processo = (
        db.query(ProcessoContrato)
        .filter(ProcessoContrato.id == processo_id, ProcessoContrato.contrato_id == contrato_id)
        .first()
    )
    if processo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    dados_informados = dados.model_dump(exclude_unset=True)
    for campo, valor in dados_informados.items():
        setattr(processo, campo, valor)

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_processo_contrato",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"processo_id": str(processo_id), "campos_alterados": list(dados_informados.keys())},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete(
    "/{contrato_id}/processos/{processo_id}",
    response_model=ContratoDetalhado,
)
def excluir_processo(
    contrato_id: uuid.UUID,
    processo_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador para não apagar dado por
    # engano.
    usuario: Usuario = Depends(exigir_administrador),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    processo = next((p for p in contrato.processos if p.id == processo_id), None)
    if processo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")
    if len(contrato.processos) == 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O contrato precisa ter ao menos um número de processo registrado.",
        )

    db.delete(processo)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_processo_contrato",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"processo_id": str(processo_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post(
    "/{contrato_id}/fornecedores", response_model=ContratoDetalhado, status_code=status.HTTP_201_CREATED
)
def adicionar_fornecedor(
    contrato_id: uuid.UUID,
    dados: FornecedorAdicionalCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Vincula mais um fornecedor ao contrato, além do principal — caso da
    locação de imóvel em que uma empresa recebe o aluguel e outra administra
    o condomínio. Cada fatura desse contrato pode então ser emitida para
    qualquer um dos fornecedores vinculados, não só o principal."""
    contrato = _carregar_contrato(db, contrato_id)
    if db.get(Fornecedor, dados.fornecedor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
    if dados.fornecedor_id == contrato.fornecedor_id or any(
        fa.fornecedor_id == dados.fornecedor_id for fa in contrato.fornecedores_adicionais
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Este fornecedor já está vinculado ao contrato."
        )

    db.add(
        FornecedorAdicionalContrato(contrato_id=contrato.id, fornecedor_id=dados.fornecedor_id, papel=dados.papel)
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="adicionar_fornecedor_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"fornecedor_id": str(dados.fornecedor_id), "papel": dados.papel},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete("/{contrato_id}/fornecedores/{vinculo_id}", response_model=ContratoDetalhado)
def excluir_fornecedor_adicional(
    contrato_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador, mesmo padrão de todo
    # vínculo do sistema.
    usuario: Usuario = Depends(exigir_administrador),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    vinculo = next((fa for fa in contrato.fornecedores_adicionais if fa.id == vinculo_id), None)
    if vinculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor adicional não encontrado.")

    db.delete(vinculo)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_fornecedor_adicional_contrato",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"vinculo_id": str(vinculo_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post("/{contrato_id}/garantia", response_model=ContratoDetalhado, status_code=status.HTTP_201_CREATED)
def registrar_garantia(
    contrato_id: uuid.UUID,
    dados: GarantiaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Registra uma nova entrada no histórico de garantia — nunca sobrescreve
    a anterior, então fica auditável quem mudou o quê e quando (mesmo
    princípio da vigência via instrumentos processuais)."""
    contrato = _carregar_contrato(db, contrato_id)
    db.add(
        GarantiaContrato(
            contrato_id=contrato.id,
            data_inicio_garantia=dados.data_inicio_garantia,
            data_fim_garantia=dados.data_fim_garantia,
            observacao=dados.observacao,
            registrado_por_id=usuario.id,
        )
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="registrar_garantia_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post(
    "/{contrato_id}/execucoes", response_model=ContratoDetalhado, status_code=status.HTTP_201_CREATED
)
def registrar_execucao(
    contrato_id: uuid.UUID,
    dados: ExecucaoCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Registra uma execução do serviço — só para contrato controlado por
    quantidade (modo_execucao = por_quantidade), como a limpeza de carpete
    aplicada N vezes no ano. Cada aplicação é uma linha nova, igual ao
    histórico de garantia; a quantidade realizada é sempre a contagem dessas
    linhas. Não bloqueia registrar além do previsto (a quantidade prevista é
    uma estimativa do termo de referência, não um limite rígido do sistema)."""
    contrato = _carregar_contrato(db, contrato_id)
    if contrato.modo_execucao != ModoExecucao.POR_QUANTIDADE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Este contrato não é controlado por quantidade de execuções.",
        )
    if contrato.status == StatusContrato.ENCERRADO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Contrato encerrado não aceita novas execuções registradas.",
        )
    db.add(
        ExecucaoContrato(
            contrato_id=contrato.id,
            data_execucao=dados.data_execucao,
            observacao=dados.observacao,
            registrado_por_id=usuario.id,
        )
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="registrar_execucao_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete(
    "/{contrato_id}/execucoes/{execucao_id}", response_model=ContratoDetalhado
)
def excluir_execucao(
    contrato_id: uuid.UUID,
    execucao_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador, para corrigir execução
    # lançada por engano, mesmo padrão de todo histórico do sistema.
    usuario: Usuario = Depends(exigir_administrador),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    execucao = next((e for e in contrato.execucoes if e.id == execucao_id), None)
    if execucao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")

    db.delete(execucao)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_execucao_contrato",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"execucao_id": str(execucao_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.patch("/{contrato_id}/pagamento", response_model=ContratoDetalhado)
def atualizar_pagamento(
    contrato_id: uuid.UUID,
    dados: ContratoAtualizarPagamento,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    contrato.valor_pago_anterior_sistema = dados.valor_pago_anterior_sistema
    # Recalcula o total somando ao que as faturas pagas no sistema já cobrem
    # — nunca sobrescreve essa parte, só a soma à parte manual.
    faturas = (
        db.query(Fatura)
        .options(selectinload(Fatura.glosas))
        .filter(Fatura.contrato_id == contrato.id)
        .all()
    )
    contrato.valor_pago = regras_faturamento.calcular_valor_pago_total(
        contrato.valor_pago_anterior_sistema, faturas
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_pagamento_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post(
    "/{contrato_id}/fiscais",
    response_model=ContratoDetalhado,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_fiscal(
    contrato_id: uuid.UUID,
    dados: FiscalVincular,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Designa um fiscal para o contrato — o fiscal pode entrar e sair da
    fiscalização ao longo do tempo (substituição), então isso é um novo
    vínculo, não uma edição do vínculo anterior."""
    contrato = _carregar_contrato(db, contrato_id)
    if db.get(Fiscal, dados.fiscal_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiscal não encontrado.")

    db.add(ContratoFiscal(contrato_id=contrato.id, fiscal_id=dados.fiscal_id, data_inicio=dados.data_inicio))
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="adicionar_fiscal_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"fiscal_id": str(dados.fiscal_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.patch(
    "/{contrato_id}/fiscais/{vinculo_id}/encerrar",
    response_model=ContratoDetalhado,
)
def encerrar_vinculo_fiscal(
    contrato_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    dados: FiscalEncerrarVinculo,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    vinculo = (
        db.query(ContratoFiscal)
        .filter(ContratoFiscal.id == vinculo_id, ContratoFiscal.contrato_id == contrato_id)
        .first()
    )
    if vinculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo de fiscal não encontrado.")
    if dados.data_fim < vinculo.data_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data de fim não pode ser anterior à data de início do vínculo.",
        )

    vinculo.data_fim = dados.data_fim
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="encerrar_vinculo_fiscal",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"vinculo_id": str(vinculo_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete(
    "/{contrato_id}/fiscais/{vinculo_id}",
    response_model=ContratoDetalhado,
)
def excluir_vinculo_fiscal(
    contrato_id: uuid.UUID,
    vinculo_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador para não apagar dado por
    # engano.
    usuario: Usuario = Depends(exigir_administrador),
) -> ContratoDetalhado:
    """Remove o vínculo por completo — diferente de encerrar (seção acima):
    é para quando o fiscal foi designado por engano nesse contrato, não para
    o caso normal de substituição (que deve usar 'encerrar', preservando o
    histórico de quem fiscalizou em cada período)."""
    vinculo = (
        db.query(ContratoFiscal)
        .filter(ContratoFiscal.id == vinculo_id, ContratoFiscal.contrato_id == contrato_id)
        .first()
    )
    if vinculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo de fiscal não encontrado.")

    db.delete(vinculo)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_vinculo_fiscal",
        entidade="contrato",
        entidade_id=str(contrato_id),
        detalhes={"vinculo_id": str(vinculo_id)},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post(
    "/{contrato_id}/instrumentos",
    response_model=ContratoDetalhado,
    status_code=status.HTTP_201_CREATED,
)
def criar_instrumento(
    contrato_id: uuid.UUID,
    dados: InstrumentoProcessualCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)

    if dados.modelo_ripm_id is not None and db.get(ModeloRipm, dados.modelo_ripm_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo RIPM não encontrado.")

    instrumento = InstrumentoProcessual(contrato_id=contrato.id, **dados.model_dump())

    # Apostilamento de reajuste: o valor mensal novo e o valor_delta (soma
    # das diferenças mensais) são sempre calculados aqui, nunca aceitos do
    # cliente — mesmo racional do contador de datas.
    if dados.reajuste_data_inicio is not None:
        try:
            distribuicao = regras_reajuste.calcular_distribuicao_reajuste(
                dados.reajuste_valor_mensal_antigo,
                dados.reajuste_indice_atual,
                dados.reajuste_indice_base,
                dados.reajuste_data_inicio,
                dados.reajuste_data_fim,
            )
        except regras_reajuste.PeriodoReajusteInvalido as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        instrumento.reajuste_valor_mensal_novo = distribuicao.valor_mensal_novo
        instrumento.valor_delta = distribuicao.valor_total_apostilamento

    try:
        regras.validar_instrumento(contrato, instrumento)
        regras.aplicar_efeitos_status(contrato, instrumento.tipo)
    except regras.TetoVigenciaExcedido as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except regras.ContratoEncerradoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    db.add(instrumento)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_instrumento_processual",
        entidade="contrato",
        entidade_id=str(contrato.id),
        detalhes={"tipo_instrumento": instrumento.tipo.value},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.patch(
    "/{contrato_id}/instrumentos/{instrumento_id}/sub-status",
    response_model=ContratoDetalhado,
)
def atualizar_sub_status_instrumento(
    contrato_id: uuid.UUID,
    instrumento_id: uuid.UUID,
    dados: InstrumentoSubStatusAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    instrumento = (
        db.query(InstrumentoProcessual)
        .filter(InstrumentoProcessual.id == instrumento_id, InstrumentoProcessual.contrato_id == contrato_id)
        .first()
    )
    if instrumento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento não encontrado.")

    instrumento.sub_status = dados.sub_status
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_sub_status_instrumento",
        entidade="instrumento_processual",
        entidade_id=str(instrumento.id),
        detalhes={"novo_sub_status": dados.sub_status.value},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.delete(
    "/{contrato_id}/instrumentos/{instrumento_id}",
    response_model=ContratoDetalhado,
)
def excluir_instrumento(
    contrato_id: uuid.UUID,
    instrumento_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador para não apagar dado por
    # engano; recalcula vigência/valor automaticamente a partir dos
    # instrumentos restantes.
    usuario: Usuario = Depends(exigir_administrador),
) -> ContratoDetalhado:
    instrumento = (
        db.query(InstrumentoProcessual)
        .filter(InstrumentoProcessual.id == instrumento_id, InstrumentoProcessual.contrato_id == contrato_id)
        .first()
    )
    if instrumento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento não encontrado.")

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_instrumento_processual",
        entidade="instrumento_processual",
        entidade_id=str(instrumento.id),
        detalhes={"tipo_instrumento": instrumento.tipo.value},
    )
    for anexo in instrumento.anexos:
        armazenamento.remover_arquivo(anexo.caminho_relativo)
    db.delete(instrumento)
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.post(
    "/{contrato_id}/instrumentos/{instrumento_id}/anexos",
    response_model=ContratoDetalhado,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_arquivo(
    contrato_id: uuid.UUID,
    instrumento_id: uuid.UUID,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    """Anexa um arquivo (contrato, termo aditivo etc. escaneados) ao
    instrumento — para visualização rápida sem precisar ir atrás do processo
    físico/SEI. Guardado em disco local (`app/uploads/`); ver nota no README
    sobre deploy sem disco persistente."""
    instrumento = (
        db.query(InstrumentoProcessual)
        .filter(InstrumentoProcessual.id == instrumento_id, InstrumentoProcessual.contrato_id == contrato_id)
        .first()
    )
    if instrumento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrumento não encontrado.")

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Arquivo vazio.")

    try:
        caminho_relativo, nome_sanitizado = armazenamento.salvar_anexo(
            instrumento.id, arquivo.filename or "arquivo", conteudo
        )
    except armazenamento.ExtensaoNaoPermitida as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    db.add(
        AnexoInstrumento(
            instrumento_id=instrumento.id,
            nome_arquivo=nome_sanitizado,
            caminho_relativo=caminho_relativo,
            tipo_mime=arquivo.content_type or "application/octet-stream",
            tamanho_bytes=len(conteudo),
            enviado_por_id=usuario.id,
        )
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="anexar_arquivo_instrumento",
        entidade="instrumento_processual",
        entidade_id=str(instrumento.id),
        detalhes={"nome_arquivo": nome_sanitizado},
    )
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))


@router.get("/{contrato_id}/auditoria", response_model=list[LogAuditoriaSaida])
def listar_auditoria_contrato(
    contrato_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[LogAuditoriaSaida]:
    contrato = _carregar_contrato(db, contrato_id)
    ids_instrumentos = [str(i.id) for i in contrato.instrumentos]

    filtro_entidades = (LogAuditoria.entidade == "contrato") & (LogAuditoria.entidade_id == str(contrato_id))
    if ids_instrumentos:
        filtro_entidades = filtro_entidades | (
            (LogAuditoria.entidade == "instrumento_processual") & (LogAuditoria.entidade_id.in_(ids_instrumentos))
        )

    logs = (
        db.query(LogAuditoria)
        .options(selectinload(LogAuditoria.usuario))
        .filter(filtro_entidades)
        .order_by(LogAuditoria.criado_em.desc())
        .limit(200)
        .all()
    )
    return [
        LogAuditoriaSaida(
            id=log.id,
            acao=log.acao,
            usuario_nome=log.usuario.nome if log.usuario else None,
            detalhes=log.detalhes,
            criado_em=log.criado_em,
        )
        for log in logs
    ]
