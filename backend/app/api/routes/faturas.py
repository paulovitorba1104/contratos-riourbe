import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.contrato import Contrato, ContratoFiscal
from app.models.faturamento import (
    ConferenciaFatura,
    EventoFatura,
    Fatura,
    GlosaFatura,
    ItemConferencia,
    MedicaoContrato,
    RegraTributaria,
    RetencaoFatura,
    StatusFatura,
    TipoEventoFatura,
    Tributo,
)
from app.models.fornecedor import Fornecedor
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.faturamento import (
    ConferenciaCriar,
    ConferenciaSaida,
    EventoSaida,
    FaturaAtualizar,
    FaturaCriar,
    FaturaDetalhada,
    FaturaSaida,
    GlosaCriar,
    GlosaSaida,
    ItemConferenciaSaida,
    LinhaPainelAnual,
    RegistrarEvento,
    RetencaoInformada,
    RetencaoSaida,
    RetencaoSugerida,
)
from app.services import contratos as regras_contratos
from app.services import faturamento as regras
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/faturas", tags=["faturas"])


# --------------------------------------------------------------------------
# Carregamento e serialização
# --------------------------------------------------------------------------
def _opcoes_fatura():
    return (
        selectinload(Fatura.glosas).selectinload(GlosaFatura.registrado_por),
        selectinload(Fatura.retencoes),
        selectinload(Fatura.eventos).selectinload(EventoFatura.responsavel),
        selectinload(Fatura.conferencias).selectinload(ConferenciaFatura.itens),
        selectinload(Fatura.conferencias).selectinload(ConferenciaFatura.conferido_por),
    )


def _carregar_fatura(db: Session, fatura_id: uuid.UUID) -> Fatura:
    fatura = db.query(Fatura).options(*_opcoes_fatura()).filter(Fatura.id == fatura_id).first()
    if fatura is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fatura não encontrada.")
    return fatura


def _contrato_com_instrumentos(db: Session, contrato_id: uuid.UUID) -> Contrato:
    contrato = (
        db.query(Contrato)
        .options(selectinload(Contrato.instrumentos), selectinload(Contrato.fiscais))
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado.")
    return contrato


def _nome_fornecedor(db: Session, contrato: Contrato) -> str:
    fornecedor = db.get(Fornecedor, contrato.fornecedor_id)
    return fornecedor.razao_social if fornecedor else "—"


def _para_saida(fatura: Fatura, contrato: Contrato, fornecedor_nome: str) -> FaturaSaida:
    alertas = regras.calcular_alertas(fatura)
    return FaturaSaida(
        id=fatura.id,
        contrato_id=fatura.contrato_id,
        contrato_numero=contrato.numero_contrato,
        fornecedor_nome=fornecedor_nome,
        medicao_id=fatura.medicao_id,
        numero_nota_fiscal=fatura.numero_nota_fiscal,
        serie=fatura.serie,
        numero_processo_sei=fatura.numero_processo_sei,
        competencia=fatura.competencia,
        data_emissao=fatura.data_emissao,
        data_recebimento=fatura.data_recebimento,
        data_vencimento=fatura.data_vencimento,
        data_envio_gco=fatura.data_envio_gco,
        data_liquidacao=fatura.data_liquidacao,
        data_pagamento=fatura.data_pagamento,
        valor_bruto=Decimal(str(fatura.valor_bruto)),
        valor_glosas=regras.total_glosas(fatura),
        valor_retencoes=regras.total_retencoes(fatura),
        valor_liquido=regras.valor_liquido(fatura),
        status=fatura.status,
        observacoes=fatura.observacoes,
        alerta_vencimento=alertas.alerta_vencimento,
        divergencia_tributaria=alertas.divergencia_tributaria,
    )


def _para_detalhada(db: Session, fatura: Fatura) -> FaturaDetalhada:
    contrato = _contrato_com_instrumentos(db, fatura.contrato_id)
    base = _para_saida(fatura, contrato, _nome_fornecedor(db, contrato))
    return FaturaDetalhada(
        **base.model_dump(),
        fatura_origem_id=fatura.fatura_origem_id,
        glosas=[
            GlosaSaida(
                id=g.id,
                valor=Decimal(str(g.valor)),
                motivo=g.motivo,
                registrado_por_nome=g.registrado_por.nome,
                registrado_em=g.registrado_em,
            )
            for g in fatura.glosas
        ],
        retencoes=[
            RetencaoSaida(
                id=r.id,
                tributo=r.tributo,
                base_calculo=Decimal(str(r.base_calculo)),
                aliquota=Decimal(str(r.aliquota)),
                valor_esperado=Decimal(str(r.valor_esperado)),
                valor_informado=Decimal(str(r.valor_informado)),
                divergente=regras.tem_divergencia(r.valor_esperado, r.valor_informado),
                observacao=r.observacao,
            )
            for r in fatura.retencoes
        ],
        conferencias=[
            ConferenciaSaida(
                id=c.id,
                modelo_checklist_id=c.modelo_checklist_id,
                conferido_por_nome=c.conferido_por.nome,
                conferido_em=c.conferido_em,
                observacoes=c.observacoes,
                itens=[ItemConferenciaSaida.model_validate(i) for i in c.itens],
            )
            for c in fatura.conferencias
        ],
        eventos=[
            EventoSaida(
                id=e.id,
                tipo=e.tipo,
                data_evento=e.data_evento,
                responsavel_nome=e.responsavel.nome,
                observacoes=e.observacoes,
            )
            for e in fatura.eventos
        ],
    )


def _erro_regra(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _sincronizar_valor_pago(db: Session, contrato: Contrato) -> None:
    """O valor pago do contrato passa a ser consequência das faturas pagas —
    aposenta o lançamento manual. Retenção não reduz execução; glosa reduz."""
    faturas = db.query(Fatura).options(selectinload(Fatura.glosas)).filter(
        Fatura.contrato_id == contrato.id
    ).all()
    contrato.valor_pago = regras.total_pago(faturas)


# --------------------------------------------------------------------------
# Faturas
# --------------------------------------------------------------------------
@router.get("", response_model=list[FaturaSaida])
def listar_faturas(
    contrato_id: uuid.UUID | None = None,
    status_filtro: StatusFatura | None = None,
    competencia: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[FaturaSaida]:
    query = db.query(Fatura).options(*_opcoes_fatura())
    if contrato_id is not None:
        query = query.filter(Fatura.contrato_id == contrato_id)
    if status_filtro is not None:
        query = query.filter(Fatura.status == status_filtro)
    if competencia:
        query = query.filter(Fatura.competencia == competencia)
    faturas = query.order_by(Fatura.data_recebimento.desc()).all()

    contratos = {c.id: c for c in db.query(Contrato).all()}
    fornecedores = {f.id: f.razao_social for f in db.query(Fornecedor).all()}
    saidas = []
    for f in faturas:
        contrato = contratos.get(f.contrato_id)
        if contrato is None:
            continue
        saidas.append(_para_saida(f, contrato, fornecedores.get(contrato.fornecedor_id, "—")))
    return saidas


@router.get("/painel-anual", response_model=list[LinhaPainelAnual])
def painel_anual(
    ano: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[LinhaPainelAnual]:
    """Matriz contrato × mês — a visão de controle que a planilha anual dava:
    para cada contrato, em que situação está a fatura de cada mês do ano."""
    contratos = db.query(Contrato).order_by(Contrato.numero_contrato).all()
    fornecedores = {f.id: f.razao_social for f in db.query(Fornecedor).all()}
    faturas = (
        db.query(Fatura)
        .filter(Fatura.competencia.like(f"{ano}-%"))
        .order_by(Fatura.data_recebimento)
        .all()
    )

    por_contrato_mes: dict[tuple[uuid.UUID, int], str] = {}
    for f in faturas:
        mes = int(f.competencia.split("-")[1])
        # Fatura cancelada não apaga o que já havia; a mais recente prevalece.
        if f.status != StatusFatura.CANCELADA or (f.contrato_id, mes) not in por_contrato_mes:
            por_contrato_mes[(f.contrato_id, mes)] = f.status.value

    linhas = []
    for c in contratos:
        _, vigencia_fim = regras_contratos.vigencia_atual(c)
        linhas.append(
            LinhaPainelAnual(
                contrato_id=c.id,
                contrato_numero=c.numero_contrato,
                fornecedor_nome=fornecedores.get(c.fornecedor_id, "—"),
                vigencia_fim=vigencia_fim,
                status_contrato=c.status.value,
                meses=[por_contrato_mes.get((c.id, m)) for m in range(1, 13)],
            )
        )
    return linhas


@router.get("/{fatura_id}", response_model=FaturaDetalhada)
def obter_fatura(
    fatura_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


@router.post("", response_model=FaturaDetalhada, status_code=status.HTTP_201_CREATED)
def criar_fatura(
    dados: FaturaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    contrato = _contrato_com_instrumentos(db, dados.contrato_id)

    try:
        regras.validar_contrato_aceita_fatura(contrato)
    except regras.RegraFaturamentoError as exc:
        raise _erro_regra(exc) from exc

    medicao = None
    if dados.medicao_id is not None:
        medicao = db.get(MedicaoContrato, dados.medicao_id)
        if medicao is None or medicao.contrato_id != contrato.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medição não encontrada neste contrato."
            )
    ja_usada = (
        dados.medicao_id is not None
        and db.query(Fatura).filter(Fatura.medicao_id == dados.medicao_id).first() is not None
    )

    existentes = db.query(Fatura).options(selectinload(Fatura.glosas)).filter(
        Fatura.contrato_id == contrato.id
    ).all()

    try:
        regras.validar_medicao(contrato, medicao, ja_usada)
        regras.validar_saldo_disponivel(
            contrato,
            existentes,
            dados.valor_bruto,
            regras_contratos.calcular_valor_atualizado(contrato),
        )
    except regras.RegraFaturamentoError as exc:
        raise _erro_regra(exc) from exc

    fatura = Fatura(**dados.model_dump(), status=StatusFatura.RECEBIDA)
    db.add(fatura)
    db.flush()

    db.add(
        EventoFatura(
            fatura_id=fatura.id,
            tipo=TipoEventoFatura.RECEBIMENTO,
            data_evento=dados.data_recebimento,
            responsavel_id=usuario.id,
        )
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_fatura",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"numero_nota_fiscal": fatura.numero_nota_fiscal, "contrato_id": str(contrato.id)},
    )
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura.id))


@router.patch("/{fatura_id}", response_model=FaturaDetalhada)
def atualizar_fatura(
    fatura_id: uuid.UUID,
    dados: FaturaAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    fatura = _carregar_fatura(db, fatura_id)
    alteracoes = dados.model_dump(exclude_unset=True)

    if "valor_bruto" in alteracoes:
        contrato = _contrato_com_instrumentos(db, fatura.contrato_id)
        outras = (
            db.query(Fatura)
            .options(selectinload(Fatura.glosas))
            .filter(Fatura.contrato_id == contrato.id, Fatura.id != fatura.id)
            .all()
        )
        try:
            regras.validar_saldo_disponivel(
                contrato,
                outras,
                alteracoes["valor_bruto"],
                regras_contratos.calcular_valor_atualizado(contrato),
            )
        except regras.RegraFaturamentoError as exc:
            raise _erro_regra(exc) from exc

    for campo, valor in alteracoes.items():
        setattr(fatura, campo, valor)

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_fatura",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"campos": sorted(alteracoes)},
    )
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


@router.delete("/{fatura_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_fatura(
    fatura_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador, como nos demais cadastros.
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    fatura = _carregar_fatura(db, fatura_id)
    contrato = _contrato_com_instrumentos(db, fatura.contrato_id)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_fatura",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"numero_nota_fiscal": fatura.numero_nota_fiscal},
    )
    db.delete(fatura)
    db.flush()
    _sincronizar_valor_pago(db, contrato)
    db.commit()


# --------------------------------------------------------------------------
# Eventos do fluxo
# --------------------------------------------------------------------------
def _registrar_evento(
    db: Session,
    fatura: Fatura,
    usuario: Usuario,
    tipo: TipoEventoFatura,
    dados: RegistrarEvento,
) -> None:
    try:
        novo_status = regras.validar_transicao(fatura, tipo)
    except regras.RegraFaturamentoError as exc:
        raise _erro_regra(exc) from exc

    fatura.status = novo_status
    db.add(
        EventoFatura(
            fatura_id=fatura.id,
            tipo=tipo,
            data_evento=dados.data_evento,
            responsavel_id=usuario.id,
            observacoes=dados.observacoes,
        )
    )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao=f"fatura_{tipo.value}",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"novo_status": novo_status.value},
    )


@router.post("/{fatura_id}/atesto", response_model=FaturaDetalhada)
def atestar_fatura(
    fatura_id: uuid.UUID,
    dados: RegistrarEvento,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    """O atesto é ato do fiscal do contrato — só quem está designado com
    vínculo vigente (ou administrador) pode atestar."""
    fatura = _carregar_fatura(db, fatura_id)
    contrato = _contrato_com_instrumentos(db, fatura.contrato_id)

    if usuario.papel != PapelUsuario.ADMINISTRADOR:
        vinculo_vigente = any(
            v.data_fim is None and _usuario_e_fiscal(db, usuario, v) for v in contrato.fiscais
        )
        if not vinculo_vigente:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="O atesto é ato do fiscal do contrato — você não está designado como fiscal vigente.",
            )

    try:
        regras.validar_conferencia_permite_atesto(fatura)
        regras.validar_divergencias_justificadas(fatura)
    except regras.RegraFaturamentoError as exc:
        raise _erro_regra(exc) from exc

    _registrar_evento(db, fatura, usuario, TipoEventoFatura.ATESTO, dados)
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


def _usuario_e_fiscal(db: Session, usuario: Usuario, vinculo: ContratoFiscal) -> bool:
    """O fiscal é cadastro próprio (não usuário do sistema); o vínculo entre os
    dois é feito pela matrícula, que é única nos dois cadastros."""
    from app.models.fiscal import Fiscal

    fiscal = db.get(Fiscal, vinculo.fiscal_id)
    if fiscal is None or not usuario.matricula:
        return False
    return fiscal.matricula == usuario.matricula


@router.post("/{fatura_id}/pagamento", response_model=FaturaDetalhada)
def registrar_pagamento(
    fatura_id: uuid.UUID,
    dados: RegistrarEvento,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    fatura = _carregar_fatura(db, fatura_id)
    _registrar_evento(db, fatura, usuario, TipoEventoFatura.PAGAMENTO, dados)
    fatura.data_pagamento = dados.data_evento
    db.flush()

    contrato = _contrato_com_instrumentos(db, fatura.contrato_id)
    _sincronizar_valor_pago(db, contrato)
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


@router.post("/{fatura_id}/devolucao", response_model=FaturaDetalhada)
def devolver_fatura(
    fatura_id: uuid.UUID,
    dados: RegistrarEvento,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    """Nota com problema volta ao fornecedor. Fica registrada com o motivo e
    pode ser reapresentada como nova fatura apontando para esta."""
    fatura = _carregar_fatura(db, fatura_id)
    if not (dados.observacoes or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o motivo da devolução.",
        )
    _registrar_evento(db, fatura, usuario, TipoEventoFatura.DEVOLUCAO, dados)
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


@router.post("/{fatura_id}/cancelamento", response_model=FaturaDetalhada)
def cancelar_fatura(
    fatura_id: uuid.UUID,
    dados: RegistrarEvento,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    fatura = _carregar_fatura(db, fatura_id)
    if not (dados.observacoes or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o motivo do cancelamento.",
        )
    _registrar_evento(db, fatura, usuario, TipoEventoFatura.CANCELAMENTO, dados)
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


# --------------------------------------------------------------------------
# Conferência documental
# --------------------------------------------------------------------------
@router.post("/{fatura_id}/conferencias", response_model=FaturaDetalhada)
def registrar_conferencia(
    fatura_id: uuid.UUID,
    dados: ConferenciaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    fatura = _carregar_fatura(db, fatura_id)

    conferencia = ConferenciaFatura(
        fatura_id=fatura.id,
        modelo_checklist_id=dados.modelo_checklist_id,
        conferido_por_id=usuario.id,
        observacoes=dados.observacoes,
    )
    db.add(conferencia)
    db.flush()
    for item in dados.itens:
        db.add(ItemConferencia(conferencia_id=conferencia.id, **item.model_dump()))
    db.flush()
    db.refresh(fatura)

    _registrar_evento(
        db,
        fatura,
        usuario,
        TipoEventoFatura.CONFERENCIA,
        RegistrarEvento(data_evento=date.today(), observacoes=dados.observacoes),
    )
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


# --------------------------------------------------------------------------
# Glosas
# --------------------------------------------------------------------------
@router.post("/{fatura_id}/glosas", response_model=FaturaDetalhada)
def registrar_glosa(
    fatura_id: uuid.UUID,
    dados: GlosaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    fatura = _carregar_fatura(db, fatura_id)
    db.add(GlosaFatura(fatura_id=fatura.id, registrado_por_id=usuario.id, **dados.model_dump()))
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="registrar_glosa_fatura",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"valor": str(dados.valor)},
    )
    db.flush()

    contrato = _contrato_com_instrumentos(db, fatura.contrato_id)
    _sincronizar_valor_pago(db, contrato)
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


@router.delete("/{fatura_id}/glosas/{glosa_id}", response_model=FaturaDetalhada)
def excluir_glosa(
    fatura_id: uuid.UUID,
    glosa_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> FaturaDetalhada:
    glosa = db.get(GlosaFatura, glosa_id)
    if glosa is None or glosa.fatura_id != fatura_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glosa não encontrada.")
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_glosa_fatura",
        entidade="fatura",
        entidade_id=str(fatura_id),
        detalhes={"valor": str(glosa.valor)},
    )
    db.delete(glosa)
    db.flush()

    fatura = _carregar_fatura(db, fatura_id)
    _sincronizar_valor_pago(db, _contrato_com_instrumentos(db, fatura.contrato_id))
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))


# --------------------------------------------------------------------------
# Conferência tributária
# --------------------------------------------------------------------------
@router.get("/{fatura_id}/retencoes/sugestao", response_model=list[RetencaoSugerida])
def sugerir_retencoes(
    fatura_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[RetencaoSugerida]:
    """Calcula o esperado de cada tributo pela regra vigente na data de emissão
    da nota — é o que a tela mostra ao lado do que veio na NF."""
    fatura = _carregar_fatura(db, fatura_id)
    todas = db.query(RegraTributaria).all()

    sugestoes = []
    for tributo in Tributo:
        regra = regras.regra_vigente(todas, tributo, fatura.data_emissao)
        if regra is None:
            continue
        calculo = regras.calcular_retencao(regra, Decimal(str(fatura.valor_bruto)))
        sugestoes.append(
            RetencaoSugerida(
                tributo=tributo,
                descricao=regra.descricao,
                base_legal=regra.base_legal,
                base_calculo=calculo.base_calculo,
                aliquota=calculo.aliquota,
                valor_esperado=calculo.valor_esperado,
            )
        )
    return sugestoes


@router.put("/{fatura_id}/retencoes", response_model=FaturaDetalhada)
def registrar_retencoes(
    fatura_id: uuid.UUID,
    dados: list[RetencaoInformada],
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> FaturaDetalhada:
    """Substitui a conferência tributária da fatura pela lista informada. Para
    cada tributo, o sistema recalcula o esperado pela regra vigente e guarda o
    que veio na nota, deixando a divergência visível."""
    fatura = _carregar_fatura(db, fatura_id)
    todas = db.query(RegraTributaria).all()

    for antiga in list(fatura.retencoes):
        db.delete(antiga)
    db.flush()

    for informada in dados:
        regra = regras.regra_vigente(todas, informada.tributo, fatura.data_emissao)
        if regra is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Não há regra tributária vigente cadastrada para {informada.tributo.value.upper()} "
                    f"na data de emissão da nota. Cadastre em Configurações → Regras tributárias."
                ),
            )
        calculo = regras.calcular_retencao(regra, Decimal(str(fatura.valor_bruto)))
        db.add(
            RetencaoFatura(
                fatura_id=fatura.id,
                tributo=informada.tributo,
                base_calculo=calculo.base_calculo,
                aliquota=calculo.aliquota,
                valor_esperado=calculo.valor_esperado,
                valor_informado=informada.valor_informado,
                observacao=informada.observacao,
            )
        )

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="conferir_tributos_fatura",
        entidade="fatura",
        entidade_id=str(fatura.id),
        detalhes={"tributos": [d.tributo.value for d in dados]},
    )
    db.commit()
    return _para_detalhada(db, _carregar_fatura(db, fatura_id))
