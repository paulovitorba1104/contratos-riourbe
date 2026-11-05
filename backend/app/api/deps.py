import uuid

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import TokenInvalido, decodificar_token, token_emitido_apos_corte
from app.db.session import get_db
from app.models.usuario import ROTULOS_MODULO, ModuloSistema, PapelUsuario, Usuario

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão inválida ou expirada. Faça login novamente.",
)


TROCA_DE_SENHA_PENDENTE = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Troque a sua senha temporária antes de continuar.",
)


def get_usuario_autenticado(
    riourbe_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Usuario:
    """Sessão válida, mesmo com troca de senha pendente. Só para as rotas que o
    usuário precisa alcançar para fazer a troca (me, trocar-senha, logout)."""
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
    if usuario is None or not usuario.ativo or usuario.aprovado_em is None:
        raise CREDENCIAIS_INVALIDAS

    if not token_emitido_apos_corte(int(payload["iat"]), usuario.sessoes_validas_apos):
        raise CREDENCIAIS_INVALIDAS

    return usuario


def get_current_user(usuario: Usuario = Depends(get_usuario_autenticado)) -> Usuario:
    if usuario.trocar_senha_obrigatorio:
        raise TROCA_DE_SENHA_PENDENTE
    return usuario


def exigir_administrador(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.papel != PapelUsuario.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação restrita a administradores.",
        )
    return usuario


_METODOS_DE_LEITURA = {"GET", "HEAD"}


def exigir_modulo(modulo: ModuloSistema, *, leitura_tambem_para: tuple[ModuloSistema, ...] = ()):
    """Libera as rotas de um módulo para administradores e para operadores com o
    módulo liberado. `leitura_tambem_para` abre só as consultas (GET) a quem tem
    outro módulo que depende desses dados — ex.: quem lança fatura precisa
    escolher o contrato, sem por isso poder editar contratos."""

    def dependencia(request: Request, usuario: Usuario = Depends(get_current_user)) -> Usuario:
        permitidos = [modulo]
        if request.method in _METODOS_DE_LEITURA:
            permitidos.extend(leitura_tambem_para)
        if any(usuario.pode_acessar(m) for m in permitidos):
            return usuario
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Você não tem acesso ao módulo {ROTULOS_MODULO[modulo]}. Fale com um administrador.",
        )

    return dependencia
