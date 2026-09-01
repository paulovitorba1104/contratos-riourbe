import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.core.security import hash_senha
from app.db.session import get_db
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.usuario import UsuarioAtualizarPapel, UsuarioBasico, UsuarioCriar, UsuarioSaida
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/usuarios", tags=["usuários"])


def _contar_administradores_ativos(db: Session, excluir_id: uuid.UUID | None = None) -> int:
    query = db.query(Usuario).filter(Usuario.papel == PapelUsuario.ADMINISTRADOR, Usuario.ativo.is_(True))
    if excluir_id is not None:
        query = query.filter(Usuario.id != excluir_id)
    return query.count()


@router.get("", response_model=list[UsuarioSaida])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_administrador),
) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.get("/basico", response_model=list[UsuarioBasico])
def listar_usuarios_basico(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Usuario]:
    """Para seleção em outros módulos (ex.: fiscais de contrato) — qualquer
    usuário autenticado, sem exigir papel de administrador."""
    return db.query(Usuario).filter(Usuario.ativo.is_(True)).order_by(Usuario.nome).all()


@router.post("", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UsuarioCriar,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    usuario = Usuario(
        nome=dados.nome,
        matricula=dados.matricula,
        cpf=dados.cpf,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
    )
    db.add(usuario)
    db.flush()
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="criar_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/papel", response_model=UsuarioSaida)
def atualizar_papel(
    usuario_id: uuid.UUID,
    dados: UsuarioAtualizarPapel,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    rebaixando_ultimo_admin = (
        usuario.papel == PapelUsuario.ADMINISTRADOR
        and dados.papel != PapelUsuario.ADMINISTRADOR
        and _contar_administradores_ativos(db, excluir_id=usuario.id) == 0
    )
    if rebaixando_ultimo_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível rebaixar o último administrador do sistema.",
        )

    usuario.papel = dados.papel
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="atualizar_papel_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
        detalhes={"novo_papel": dados.papel.value},
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_usuario(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> None:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    if (
        usuario.papel == PapelUsuario.ADMINISTRADOR
        and _contar_administradores_ativos(db, excluir_id=usuario.id) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível remover o último administrador do sistema.",
        )

    usuario.ativo = False
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="desativar_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
    )
    db.commit()
