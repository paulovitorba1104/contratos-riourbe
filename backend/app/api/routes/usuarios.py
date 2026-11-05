import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador
from app.db.session import get_db
from app.models.usuario import PapelUsuario, SituacaoUsuario, Usuario
from app.schemas.usuario import AcessoUsuario, SenhaTemporariaSaida, UsuarioCriar, UsuarioSaida
from app.services.auditoria import registrar_log
from app.services.senhas import aplicar_senha_temporaria

router = APIRouter(prefix="/usuarios", tags=["usuários"])

ULTIMO_ADMINISTRADOR = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="O sistema precisa de pelo menos um administrador ativo.",
)


def _contar_administradores_ativos(db: Session, excluir_id: uuid.UUID | None = None) -> int:
    query = db.query(Usuario).filter(
        Usuario.papel == PapelUsuario.ADMINISTRADOR,
        Usuario.ativo.is_(True),
        Usuario.aprovado_em.is_not(None),
    )
    if excluir_id is not None:
        query = query.filter(Usuario.id != excluir_id)
    return query.count()


def _obter(db: Session, usuario_id: uuid.UUID) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return usuario


def _aplicar_acesso(usuario: Usuario, acesso: AcessoUsuario | UsuarioCriar) -> None:
    usuario.papel = acesso.papel
    usuario.modulos = [m.value for m in acesso.modulos]


def _detalhes_acesso(usuario: Usuario) -> dict:
    return {"papel": usuario.papel.value, "modulos": list(usuario.modulos)}


@router.get("", response_model=list[UsuarioSaida])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_administrador),
) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.post("", response_model=SenhaTemporariaSaida, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    dados: UsuarioCriar,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> SenhaTemporariaSaida:
    """Cadastro direto pelo administrador: já nasce aprovado, com papel e módulos
    definidos, e com uma senha temporária para o usuário trocar no primeiro acesso."""
    usuario = Usuario(
        nome=dados.nome,
        matricula=dados.matricula,
        cpf=dados.cpf,
        email=dados.email,
        senha_hash="",
        aprovado_em=datetime.now(UTC),
    )
    _aplicar_acesso(usuario, dados)
    senha_temporaria = aplicar_senha_temporaria(usuario)
    db.add(usuario)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esta matrícula, CPF ou e-mail.",
        ) from exc

    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="criar_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
        detalhes=_detalhes_acesso(usuario),
    )
    db.commit()
    db.refresh(usuario)
    return SenhaTemporariaSaida(usuario=UsuarioSaida.model_validate(usuario), senha_temporaria=senha_temporaria)


@router.post("/{usuario_id}/aprovar", response_model=UsuarioSaida)
def aprovar_cadastro(
    usuario_id: uuid.UUID,
    dados: AcessoUsuario,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    """Aprova um pedido de acesso feito pela tela de login (também serve para
    voltar atrás num pedido recusado), já definindo papel e módulos."""
    usuario = _obter(db, usuario_id)
    if usuario.aprovado_em is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este cadastro já foi aprovado.")

    usuario.aprovado_em = datetime.now(UTC)
    usuario.ativo = True
    _aplicar_acesso(usuario, dados)
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="aprovar_cadastro_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
        detalhes=_detalhes_acesso(usuario),
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/{usuario_id}/recusar", response_model=UsuarioSaida)
def recusar_cadastro(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    """Recusa um pedido pendente. O registro fica (dá para aprovar depois, se
    foi engano), mas a pessoa não consegue entrar."""
    usuario = _obter(db, usuario_id)
    if usuario.situacao != SituacaoUsuario.PENDENTE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só um pedido pendente pode ser recusado.")

    usuario.ativo = False
    registrar_log(
        db, usuario_id=administrador.id, acao="recusar_cadastro_usuario", entidade="usuario", entidade_id=str(usuario.id)
    )
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/acesso", response_model=UsuarioSaida)
def atualizar_acesso(
    usuario_id: uuid.UUID,
    dados: AcessoUsuario,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    """Muda papel e módulos de um usuário já aprovado. Vale na hora: o acesso é
    conferido a cada requisição, sem precisar sair e entrar de novo."""
    usuario = _obter(db, usuario_id)
    if usuario.aprovado_em is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cadastro ainda não aprovado — use Aprovar."
        )

    rebaixando_ultimo_admin = (
        usuario.papel == PapelUsuario.ADMINISTRADOR
        and dados.papel != PapelUsuario.ADMINISTRADOR
        and usuario.ativo
        and _contar_administradores_ativos(db, excluir_id=usuario.id) == 0
    )
    if rebaixando_ultimo_admin:
        raise ULTIMO_ADMINISTRADOR

    _aplicar_acesso(usuario, dados)
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="atualizar_acesso_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
        detalhes=_detalhes_acesso(usuario),
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
    usuario = _obter(db, usuario_id)
    if usuario.id == administrador.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Para a sua própria senha, use "Trocar senha".',
        )
    if usuario.situacao != SituacaoUsuario.ATIVO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário não está ativo.")

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


@router.post("/{usuario_id}/reativar", response_model=UsuarioSaida)
def reativar_usuario(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
) -> Usuario:
    usuario = _obter(db, usuario_id)
    if usuario.situacao != SituacaoUsuario.DESATIVADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só um usuário desativado pode ser reativado.")

    usuario.ativo = True
    registrar_log(
        db, usuario_id=administrador.id, acao="reativar_usuario", entidade="usuario", entidade_id=str(usuario.id)
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
    usuario = _obter(db, usuario_id)
    if usuario.id == administrador.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Você não pode desativar o seu próprio usuário.")
    if usuario.situacao != SituacaoUsuario.ATIVO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Só um usuário ativo pode ser desativado.")
    if usuario.papel == PapelUsuario.ADMINISTRADOR and _contar_administradores_ativos(db, excluir_id=usuario.id) == 0:
        raise ULTIMO_ADMINISTRADOR

    usuario.ativo = False
    registrar_log(
        db,
        usuario_id=administrador.id,
        acao="desativar_usuario",
        entidade="usuario",
        entidade_id=str(usuario.id),
    )
    db.commit()
