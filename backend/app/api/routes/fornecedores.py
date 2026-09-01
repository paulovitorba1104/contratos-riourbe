from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.fornecedor import Fornecedor
from app.models.usuario import Usuario
from app.schemas.fornecedor import FornecedorCriar, FornecedorSaida

router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])


@router.get("", response_model=list[FornecedorSaida])
def listar_fornecedores(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Fornecedor]:
    return db.query(Fornecedor).order_by(Fornecedor.razao_social).all()


@router.post("", response_model=FornecedorSaida, status_code=status.HTTP_201_CREATED)
def criar_fornecedor(
    dados: FornecedorCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Fornecedor:
    fornecedor = Fornecedor(razao_social=dados.razao_social, cnpj=dados.cnpj)
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor
