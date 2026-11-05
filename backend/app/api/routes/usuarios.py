import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador
from app.core.security import hash_senha
from app.db.session import get_db
from app.models.usuario import PapelUsuario, Usuario
from app.schemas.usuario import SenhaTemporariaSaida, UsuarioAtualizarPapel, UsuarioCriar, UsuarioSaida
from app.services.auditoria import registrar_log
from app.services.senhas import aplicar_senha_temporaria

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


@router.post("/{usuario_id}/redefinir-senha", response_model=SenhaTemporariaSaida)
def redefinir_senha(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> SenhaTemporariaSaida:
    """Redefinição sem e-mail: gera uma senha temporária, devolvida só nesta
    resposta para o administrador repassar ao usuário, que é obrigado a trocá-la
    no próximo login."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if usuario.id == administrador.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Para a sua própria senha, use "Trocar senha".',
        )
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário desativado.")

    senha_temporaria = aplicar_senha_temporaria(usuario)
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="redefinir_senha_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
    )
    db.commit()
    db.refresh(usuario)
    return SenhaTemporariaSaida(usuario=UsuarioSaida.model_validate(usuario), senha_temporaria=senha_temporaria)


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
