import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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


@router.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_modelo_ripm(
    modelo_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador; se o modelo já estiver
    # usado em algum instrumento, o banco recusa (chave estrangeira) e o
    # handler global devolve 409.
    _: Usuario = Depends(exigir_administrador),
) -> None:
    modelo = db.get(ModeloRipm, modelo_id)
    if modelo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo RIPM não encontrado.")
    db.delete(modelo)
    db.commit()
