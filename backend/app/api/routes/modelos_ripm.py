from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.modelo_ripm import ModeloRipm
from app.models.usuario import Usuario
from app.schemas.modelo_ripm import ModeloRipmCriar, ModeloRipmSaida

router = APIRouter(prefix="/modelos-ripm", tags=["modelos RIPM"])


@router.get("", response_model=list[ModeloRipmSaida])
def listar_modelos_ripm(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[ModeloRipm]:
    return db.query(ModeloRipm).filter(ModeloRipm.ativo.is_(True)).order_by(ModeloRipm.codigo).all()


@router.post("", response_model=ModeloRipmSaida, status_code=status.HTTP_201_CREATED)
def criar_modelo_ripm(
    dados: ModeloRipmCriar,
    db: Session = Depends(get_db),
    # Cadastro de referência normativa — restrito a administrador.
    _: Usuario = Depends(exigir_administrador),
) -> ModeloRipm:
    modelo = ModeloRipm(
        codigo=dados.codigo,
        nome=dados.nome,
        itens_checklist=dados.itens_checklist,
        ativo=dados.ativo,
    )
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo
