import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.fiscal import Fiscal
from app.models.usuario import Usuario
from app.schemas.fiscal import FiscalAtualizar, FiscalCriar, FiscalSaida

router = APIRouter(prefix="/fiscais", tags=["fiscais"])


@router.get("", response_model=list[FiscalSaida])
def listar_fiscais(
    apenas_ativos: bool = True,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Fiscal]:
    query = db.query(Fiscal)
    if apenas_ativos:
        query = query.filter(Fiscal.ativo.is_(True))
    return query.order_by(Fiscal.nome).all()


@router.post("", response_model=FiscalSaida, status_code=status.HTTP_201_CREATED)
def criar_fiscal(
    dados: FiscalCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Fiscal:
    fiscal = Fiscal(nome=dados.nome, matricula=dados.matricula, cpf=dados.cpf)
    db.add(fiscal)
    db.commit()
    db.refresh(fiscal)
    return fiscal


@router.patch("/{fiscal_id}", response_model=FiscalSaida)
def atualizar_fiscal(
    fiscal_id: uuid.UUID,
    dados: FiscalAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Fiscal:
    fiscal = db.get(Fiscal, fiscal_id)
    if fiscal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiscal não encontrado.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(fiscal, campo, valor)
    db.commit()
    db.refresh(fiscal)
    return fiscal


@router.delete("/{fiscal_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_fiscal(
    fiscal_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador para não apagar dado por
    # engano; se o fiscal já foi vinculado a algum contrato, o banco recusa
    # (chave estrangeira) e o handler global devolve 409.
    _: Usuario = Depends(exigir_administrador),
) -> None:
    fiscal = db.get(Fiscal, fiscal_id)
    if fiscal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiscal não encontrado.")
    db.delete(fiscal)
    db.commit()
