"""Medições e a configuração do módulo de Faturamento.

As regras tributárias ficam aqui de propósito: alíquota, base e fundamentação
legal são **cadastro**, não código — quando a legislação muda, muda o cadastro,
sem precisar de nova versão do sistema.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.contrato import Contrato
from app.models.faturamento import (
    Fatura,
    ItemModeloChecklist,
    MedicaoContrato,
    ModeloChecklist,
    RegraTributaria,
    StatusMedicao,
)
from app.models.usuario import Usuario
from app.schemas.faturamento import (
    MedicaoAtualizar,
    MedicaoCriar,
    MedicaoSaida,
    ModeloChecklistAtualizar,
    ModeloChecklistCriar,
    ModeloChecklistSaida,
    RegraTributariaAtualizar,
    RegraTributariaCriar,
    RegraTributariaSaida,
)
from app.services.auditoria import registrar_log

router_medicoes = APIRouter(prefix="/medicoes", tags=["faturas"])
router_regras = APIRouter(prefix="/regras-tributarias", tags=["faturas"])
router_modelos = APIRouter(prefix="/modelos-checklist", tags=["faturas"])


# --------------------------------------------------------------------------
# Medições
# --------------------------------------------------------------------------
def _para_saida_medicao(medicao: MedicaoContrato) -> MedicaoSaida:
    return MedicaoSaida(
        id=medicao.id,
        contrato_id=medicao.contrato_id,
        numero_medicao=medicao.numero_medicao,
        competencia=medicao.competencia,
        periodo_inicio=medicao.periodo_inicio,
        periodo_fim=medicao.periodo_fim,
        valor_medido=medicao.valor_medido,
        status=medicao.status,
        aprovado_por_nome=medicao.aprovado_por.nome if medicao.aprovado_por else None,
        aprovado_em=medicao.aprovado_em,
        observacoes=medicao.observacoes,
    )


def _carregar_medicao(db: Session, medicao_id: uuid.UUID) -> MedicaoContrato:
    medicao = (
        db.query(MedicaoContrato)
        .options(selectinload(MedicaoContrato.aprovado_por))
        .filter(MedicaoContrato.id == medicao_id)
        .first()
    )
    if medicao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medição não encontrada.")
    return medicao


@router_medicoes.get("", response_model=list[MedicaoSaida])
def listar_medicoes(
    contrato_id: uuid.UUID | None = None,
    apenas_disponiveis: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[MedicaoSaida]:
    """`apenas_disponiveis` traz só as medições aprovadas que ainda não foram
    usadas por nenhuma fatura — é o que a tela de nova fatura precisa."""
    query = db.query(MedicaoContrato).options(selectinload(MedicaoContrato.aprovado_por))
    if contrato_id is not None:
        query = query.filter(MedicaoContrato.contrato_id == contrato_id)
    medicoes = query.order_by(MedicaoContrato.competencia.desc()).all()

    if apenas_disponiveis:
        usadas = {f.medicao_id for f in db.query(Fatura).filter(Fatura.medicao_id.isnot(None)).all()}
        medicoes = [
            m for m in medicoes if m.status == StatusMedicao.APROVADA and m.id not in usadas
        ]
    return [_para_saida_medicao(m) for m in medicoes]


@router_medicoes.post("", response_model=MedicaoSaida, status_code=status.HTTP_201_CREATED)
def criar_medicao(
    dados: MedicaoCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> MedicaoSaida:
    if db.get(Contrato, dados.contrato_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado.")
    if dados.periodo_fim < dados.periodo_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O fim do período medido não pode ser anterior ao início.",
        )

    medicao = MedicaoContrato(**dados.model_dump())
    db.add(medicao)
    db.flush()
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_medicao",
        entidade="medicao",
        entidade_id=str(medicao.id),
        detalhes={"contrato_id": str(dados.contrato_id), "competencia": dados.competencia},
    )
    db.commit()
    return _para_saida_medicao(_carregar_medicao(db, medicao.id))


@router_medicoes.patch("/{medicao_id}", response_model=MedicaoSaida)
def atualizar_medicao(
    medicao_id: uuid.UUID,
    dados: MedicaoAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> MedicaoSaida:
    medicao = _carregar_medicao(db, medicao_id)
    if medicao.status == StatusMedicao.APROVADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Medição aprovada não pode ser alterada — rejeite antes de corrigir.",
        )
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(medicao, campo, valor)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_medicao",
        entidade="medicao",
        entidade_id=str(medicao.id),
    )
    db.commit()
    return _para_saida_medicao(_carregar_medicao(db, medicao_id))


@router_medicoes.post("/{medicao_id}/aprovar", response_model=MedicaoSaida)
def aprovar_medicao(
    medicao_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> MedicaoSaida:
    medicao = _carregar_medicao(db, medicao_id)
    medicao.status = StatusMedicao.APROVADA
    medicao.aprovado_por_id = usuario.id
    medicao.aprovado_em = datetime.now(timezone.utc)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="aprovar_medicao",
        entidade="medicao",
        entidade_id=str(medicao.id),
    )
    db.commit()
    return _para_saida_medicao(_carregar_medicao(db, medicao_id))


@router_medicoes.post("/{medicao_id}/rejeitar", response_model=MedicaoSaida)
def rejeitar_medicao(
    medicao_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> MedicaoSaida:
    medicao = _carregar_medicao(db, medicao_id)
    if db.query(Fatura).filter(Fatura.medicao_id == medicao.id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Esta medição já foi usada por uma fatura e não pode ser rejeitada.",
        )
    medicao.status = StatusMedicao.REJEITADA
    medicao.aprovado_por_id = None
    medicao.aprovado_em = None
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="rejeitar_medicao",
        entidade="medicao",
        entidade_id=str(medicao.id),
    )
    db.commit()
    return _para_saida_medicao(_carregar_medicao(db, medicao_id))


@router_medicoes.delete("/{medicao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_medicao(
    medicao_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    medicao = _carregar_medicao(db, medicao_id)
    if db.query(Fatura).filter(Fatura.medicao_id == medicao.id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta medição está vinculada a uma fatura e não pode ser excluída.",
        )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_medicao",
        entidade="medicao",
        entidade_id=str(medicao.id),
    )
    db.delete(medicao)
    db.commit()


# --------------------------------------------------------------------------
# Regras tributárias
# --------------------------------------------------------------------------
@router_regras.get("", response_model=list[RegraTributariaSaida])
def listar_regras(
    apenas_ativas: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[RegraTributariaSaida]:
    query = db.query(RegraTributaria)
    if apenas_ativas:
        query = query.filter(RegraTributaria.ativo.is_(True))
    regras = query.order_by(RegraTributaria.tributo, RegraTributaria.vigencia_inicio.desc()).all()
    return [RegraTributariaSaida.model_validate(r) for r in regras]


@router_regras.post("", response_model=RegraTributariaSaida, status_code=status.HTTP_201_CREATED)
def criar_regra(
    dados: RegraTributariaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> RegraTributariaSaida:
    if dados.vigencia_fim and dados.vigencia_fim < dados.vigencia_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O fim da vigência não pode ser anterior ao início.",
        )
    regra = RegraTributaria(**dados.model_dump())
    db.add(regra)
    db.flush()
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_regra_tributaria",
        entidade="regra_tributaria",
        entidade_id=str(regra.id),
        detalhes={"tributo": dados.tributo.value, "aliquota": str(dados.aliquota)},
    )
    db.commit()
    db.refresh(regra)
    return RegraTributariaSaida.model_validate(regra)


@router_regras.patch("/{regra_id}", response_model=RegraTributariaSaida)
def atualizar_regra(
    regra_id: uuid.UUID,
    dados: RegraTributariaAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> RegraTributariaSaida:
    regra = db.get(RegraTributaria, regra_id)
    if regra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(regra, campo, valor)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_regra_tributaria",
        entidade="regra_tributaria",
        entidade_id=str(regra.id),
    )
    db.commit()
    db.refresh(regra)
    return RegraTributariaSaida.model_validate(regra)


@router_regras.delete("/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_regra(
    regra_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    regra = db.get(RegraTributaria, regra_id)
    if regra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada.")
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_regra_tributaria",
        entidade="regra_tributaria",
        entidade_id=str(regra.id),
    )
    db.delete(regra)
    db.commit()


# --------------------------------------------------------------------------
# Modelos de checklist
# --------------------------------------------------------------------------
def _carregar_modelo(db: Session, modelo_id: uuid.UUID) -> ModeloChecklist:
    modelo = (
        db.query(ModeloChecklist)
        .options(selectinload(ModeloChecklist.itens))
        .filter(ModeloChecklist.id == modelo_id)
        .first()
    )
    if modelo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado.")
    return modelo


@router_modelos.get("", response_model=list[ModeloChecklistSaida])
def listar_modelos(
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[ModeloChecklistSaida]:
    query = db.query(ModeloChecklist).options(selectinload(ModeloChecklist.itens))
    if apenas_ativos:
        query = query.filter(ModeloChecklist.ativo.is_(True))
    return [
        ModeloChecklistSaida.model_validate(m) for m in query.order_by(ModeloChecklist.nome).all()
    ]


@router_modelos.post("", response_model=ModeloChecklistSaida, status_code=status.HTTP_201_CREATED)
def criar_modelo(
    dados: ModeloChecklistCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> ModeloChecklistSaida:
    modelo = ModeloChecklist(nome=dados.nome, descricao=dados.descricao)
    db.add(modelo)
    db.flush()
    for indice, item in enumerate(dados.itens):
        db.add(
            ItemModeloChecklist(
                modelo_id=modelo.id,
                descricao=item.descricao,
                obrigatorio=item.obrigatorio,
                ordem=item.ordem or indice,
            )
        )
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="criar_modelo_checklist",
        entidade="modelo_checklist",
        entidade_id=str(modelo.id),
        detalhes={"nome": dados.nome, "itens": len(dados.itens)},
    )
    db.commit()
    return ModeloChecklistSaida.model_validate(_carregar_modelo(db, modelo.id))


@router_modelos.patch("/{modelo_id}", response_model=ModeloChecklistSaida)
def atualizar_modelo(
    modelo_id: uuid.UUID,
    dados: ModeloChecklistAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> ModeloChecklistSaida:
    modelo = _carregar_modelo(db, modelo_id)
    alteracoes = dados.model_dump(exclude_unset=True)
    itens = alteracoes.pop("itens", None)

    for campo, valor in alteracoes.items():
        setattr(modelo, campo, valor)

    if itens is not None:
        for antigo in list(modelo.itens):
            db.delete(antigo)
        db.flush()
        for indice, item in enumerate(itens):
            db.add(
                ItemModeloChecklist(
                    modelo_id=modelo.id,
                    descricao=item["descricao"],
                    obrigatorio=item["obrigatorio"],
                    ordem=item["ordem"] or indice,
                )
            )

    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="atualizar_modelo_checklist",
        entidade="modelo_checklist",
        entidade_id=str(modelo.id),
    )
    db.commit()
    return ModeloChecklistSaida.model_validate(_carregar_modelo(db, modelo_id))


@router_modelos.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_modelo(
    modelo_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    modelo = _carregar_modelo(db, modelo_id)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_modelo_checklist",
        entidade="modelo_checklist",
        entidade_id=str(modelo.id),
        detalhes={"nome": modelo.nome},
    )
    db.delete(modelo)
    db.commit()
