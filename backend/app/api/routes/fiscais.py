from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.fiscal import Fiscal
from app.models.usuario import Usuario
from app.schemas.fiscal import FiscalCriar, FiscalSaida

router = APIRouter(prefix="/fiscais", tags=["fiscais"])


@router.get("", response_model=list[FiscalSaida])
def listar_fiscais(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Fiscal]:
    return db.query(Fiscal).filter(Fiscal.ativo.is_(True)).order_by(Fiscal.nome).all()


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
