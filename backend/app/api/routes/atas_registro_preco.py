import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.ata_registro_preco import AtaRegistroPreco
from app.models.usuario import Usuario
from app.schemas.ata_registro_preco import (
    AtaRegistroPrecoAtualizar,
    AtaRegistroPrecoCriar,
    AtaRegistroPrecoSaida,
)

router = APIRouter(prefix="/atas-registro-preco", tags=["atas de registro de preço"])


@router.get("", response_model=list[AtaRegistroPrecoSaida])
def listar_atas(
    apenas_disponiveis: bool = True,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[AtaRegistroPreco]:
    query = db.query(AtaRegistroPreco)
    if apenas_disponiveis:
        query = query.filter(AtaRegistroPreco.disponivel_para_adesao.is_(True))
    return query.order_by(AtaRegistroPreco.data_validade).all()


@router.post("", response_model=AtaRegistroPrecoSaida, status_code=status.HTTP_201_CREATED)
def criar_ata(
    dados: AtaRegistroPrecoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> AtaRegistroPreco:
    ata = AtaRegistroPreco(**dados.model_dump())
    db.add(ata)
    db.commit()
    db.refresh(ata)
    return ata


@router.patch("/{ata_id}", response_model=AtaRegistroPrecoSaida)
def atualizar_ata(
    ata_id: uuid.UUID,
    dados: AtaRegistroPrecoAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> AtaRegistroPreco:
    ata = db.get(AtaRegistroPreco, ata_id)
    if ata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ata não encontrada.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(ata, campo, valor)
    db.commit()
    db.refresh(ata)
    return ata


@router.delete("/{ata_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_ata(
    ata_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_administrador),
) -> None:
    ata = db.get(AtaRegistroPreco, ata_id)
    if ata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ata não encontrada.")
    db.delete(ata)
    db.commit()
