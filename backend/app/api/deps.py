import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import TokenInvalido, decodificar_token, token_emitido_apos_corte
from app.db.session import get_db
from app.models.usuario import PapelUsuario, Usuario

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada. Faça login novamente.",
)


def get_current_user(
    riourbe_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Usuario:
    if not riourbe_session:
        raise CREDENCIAIS_INVALIDAS

    try:
        payload = decodificar_token(riourbe_session, settings)
    except TokenInvalido as exc:
        raise CREDENCIAIS_INVALIDAS from exc

    try:
        usuario_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise CREDENCIAIS_INVALIDAS from exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise CREDENCIAIS_INVALIDAS

    if not token_emitido_apos_corte(int(payload["iat"]), usuario.sessoes_validas_apos):
        raise CREDENCIAIS_INVALIDAS

    return usuario


def exigir_administrador(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.papel != PapelUsuario.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação restrita a administradores.",
        )
    return usuario
