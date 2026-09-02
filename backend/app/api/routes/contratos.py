import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.contrato import Contrato, ContratoFiscal, GarantiaContrato, ProcessoContrato, StatusContrato
from app.models.fiscal import Fiscal
from app.models.fornecedor import Fornecedor
from app.models.instrumento_processual import InstrumentoProcessual, TipoInstrumento
from app.models.modelo_ripm import ModeloRipm
from app.models.usuario import Usuario
from app.schemas.contrato import (
    ContratoAtualizar,
    ContratoAtualizarPagamento,
    ContratoCriar,
    ContratoDetalhado,
    ContratoSaida,
    GarantiaCriar,
    GarantiaSaida,
    ProcessoAtualizar,
    ProcessoCriar,
)
from app.schemas.fiscal import FiscalEncerrarVinculo, FiscalVincular, FiscalVinculoSaida
from app.schemas.instrumento import InstrumentoProcessualCriar, InstrumentoSubStatusAtualizar
from app.services import contratos as regras
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/contratos", tags=["contratos"])


def _carregar_contrato(db: Session, contrato_id: uuid.UUID) -> Contrato:
    contrato = (
        db.query(Contrato)
        .options(
            selectinload(Contrato.instrumentos),
            selectinload(Contrato.fiscais).selectinload(ContratoFiscal.fiscal),
            selectinload(Contrato.garantias).selectinload(GarantiaContrato.registrado_por),
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
            if campo not in {"alerta_vigencia", "alerta_garantia"}
        },
        alerta_vigencia=alertas.alerta_vigencia,
        alerta_garantia=alertas.alerta_garantia,
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
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        teto_vigencia=regras.teto_vigencia(contrato),
        garantia_inicio=garantia_inicio,
        garantia_fim=garantia_fim,
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
        instrumentos=list(contrato.instrumentos),
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

    for campo, valor in dados_informados.items():
        setattr(contrato, campo, valor)

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
    db.delete(instrumento)
    db.commit()
    return _para_detalhado(_carregar_contrato(db, contrato_id))
