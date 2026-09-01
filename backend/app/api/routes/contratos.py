import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.contrato import Contrato, ContratoFiscal, StatusContrato
from app.models.fornecedor import Fornecedor
from app.models.instrumento_processual import InstrumentoProcessual
from app.models.modelo_ripm import ModeloRipm
from app.models.usuario import Usuario
from app.schemas.contrato import (
    ContratoAtualizarGarantia,
    ContratoAtualizarPagamento,
    ContratoCriar,
    ContratoDetalhado,
    ContratoSaida,
)
from app.schemas.instrumento import InstrumentoProcessualCriar, InstrumentoSubStatusAtualizar
from app.services import contratos as regras
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/contratos", tags=["contratos"])


def _carregar_contrato(db: Session, contrato_id: uuid.UUID) -> Contrato:
    contrato = (
        db.query(Contrato)
        .options(selectinload(Contrato.instrumentos), selectinload(Contrato.fiscais))
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado.")
    return contrato


def _para_detalhado(contrato: Contrato) -> ContratoDetalhado:
    alertas = regras.calcular_alertas(contrato)
    vigencia_inicio, vigencia_fim = regras.vigencia_atual(contrato)
    return ContratoDetalhado(
        **ContratoSaida.model_validate(contrato).model_dump(),
        fiscais_ids=[f.usuario_id for f in contrato.fiscais],
        valor_atualizado=regras.calcular_valor_atualizado(contrato),
        saldo_a_pagar=regras.calcular_saldo_a_pagar(contrato),
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        teto_vigencia=regras.teto_vigencia(contrato),
        alerta_vigencia=alertas.alerta_vigencia,
        alerta_garantia=alertas.alerta_garantia,
        instrumentos=list(contrato.instrumentos),
    )


@router.get("", response_model=list[ContratoSaida])
def listar_contratos(
    status_filtro: StatusContrato | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Contrato]:
    query = db.query(Contrato)
    if status_filtro is not None:
        query = query.filter(Contrato.status == status_filtro)
    return query.order_by(Contrato.criado_em.desc()).all()


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

    fiscais_encontrados = (
        db.query(Usuario.id).filter(Usuario.id.in_(dados.fiscais_ids)).all()
    )
    if len(fiscais_encontrados) != len(set(dados.fiscais_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Um ou mais fiscais não encontrados.")

    contrato = Contrato(
        **dados.model_dump(exclude={"fiscais_ids"}),
    )
    db.add(contrato)
    db.flush()

    for fiscal_id in set(dados.fiscais_ids):
        db.add(ContratoFiscal(contrato_id=contrato.id, usuario_id=fiscal_id))

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
    )
    db.commit()

    return _para_detalhado(_carregar_contrato(db, contrato.id))


@router.patch("/{contrato_id}/garantia", response_model=ContratoDetalhado)
def atualizar_garantia(
    contrato_id: uuid.UUID,
    dados: ContratoAtualizarGarantia,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ContratoDetalhado:
    contrato = _carregar_contrato(db, contrato_id)
    contrato.data_inicio_garantia = dados.data_inicio_garantia
    contrato.data_fim_garantia = dados.data_fim_garantia
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_garantia_contrato",
        entidade="contrato",
        entidade_id=str(contrato.id),
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
    contrato.valor_pago = dados.valor_pago
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

    if db.get(ModeloRipm, dados.modelo_ripm_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo RIPM não encontrado.")

    instrumento = InstrumentoProcessual(contrato_id=contrato.id, **dados.model_dump())

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
