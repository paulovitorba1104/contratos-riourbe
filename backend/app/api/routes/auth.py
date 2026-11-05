from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_autenticado
from app.core.config import Settings, get_settings
from app.core.rate_limit import (
    LoginBloqueado,
    limpar_falhas_login,
    registrar_falha_login,
    verificar_bloqueio_login,
)
from app.core.security import (
    TipoIdentificador,
    criar_token_acesso,
    detectar_tipo_identificador,
    normalizar_cpf,
    verificar_senha,
)
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, LoginResponse, TrocarSenhaRequest, UsuarioPublico
from app.services.auditoria import registrar_log
from app.services.senhas import aplicar_nova_senha

router = APIRouter(prefix="/auth", tags=["autenticação"])

MENSAGEM_ERRO_GENERICA = "Identificador ou senha inválidos."


def _obter_ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _buscar_usuario(db: Session, identificador: str) -> Usuario | None:
    tipo = detectar_tipo_identificador(identificador)
    if tipo == TipoIdentificador.CPF:
        return db.query(Usuario).filter(Usuario.cpf == normalizar_cpf(identificador)).first()
    return db.query(Usuario).filter(Usuario.matricula == identificador).first()


def _emitir_cookie_sessao(response: Response, usuario: Usuario, settings: Settings) -> None:
    token, expira_em = criar_token_acesso(str(usuario.id), settings)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expira_horas * 3600,
        expires=expira_em,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def login(
    dados: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    ip = _obter_ip(request)

    try:
        verificar_bloqueio_login(ip, dados.identificador)
    except LoginBloqueado as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        ) from exc

    usuario = _buscar_usuario(db, dados.identificador)
    senha_confere = verificar_senha(dados.senha, usuario.senha_hash if usuario else None)

    if usuario is None or not usuario.ativo or not senha_confere:
        registrar_falha_login(ip, dados.identificador)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAGEM_ERRO_GENERICA)

    limpar_falhas_login(ip, dados.identificador)

    _emitir_cookie_sessao(response, usuario, settings)

    registrar_log(db, usuario_id=usuario.id, acao="login", entidade="usuario", entidade_id=str(usuario.id))
    db.commit()

    return LoginResponse(usuario=UsuarioPublico.model_validate(usuario))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    usuario: Usuario = Depends(get_usuario_autenticado),
) -> None:
    # Corte de revogação server-side: invalida qualquer token emitido antes de agora.
    usuario.sessoes_validas_apos = datetime.now(UTC)
    registrar_log(db, usuario_id=usuario.id, acao="logout", entidade="usuario", entidade_id=str(usuario.id))
    db.commit()
    response.delete_cookie(key=settings.cookie_name, path="/")


@router.get("/me", response_model=UsuarioPublico)
def me(usuario: Usuario = Depends(get_usuario_autenticado)) -> UsuarioPublico:
    return UsuarioPublico.model_validate(usuario)


@router.post("/trocar-senha", response_model=UsuarioPublico)
def trocar_senha(
    dados: TrocarSenhaRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    usuario: Usuario = Depends(get_usuario_autenticado),
) -> UsuarioPublico:
    """Troca feita pelo próprio usuário — voluntária ou obrigatória depois de uma
    senha temporária. Exige a senha atual, com o mesmo limite de tentativas do
    login, para uma sessão esquecida aberta não bastar para tomar a conta."""
    ip = _obter_ip(request)
    chave_conta = usuario.matricula or usuario.cpf

    try:
        verificar_bloqueio_login(ip, chave_conta)
    except LoginBloqueado as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente mais tarde.",
        ) from exc

    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        registrar_falha_login(ip, chave_conta)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")

    limpar_falhas_login(ip, chave_conta)
    aplicar_nova_senha(usuario, dados.nova_senha)
    registrar_log(db, usuario_id=usuario.id, acao="trocar_senha", entidade="usuario", entidade_id=str(usuario.id))
    db.commit()
    db.refresh(usuario)

    # As outras sessões caem pelo corte de revogação; esta continua com um token novo.
    _emitir_cookie_sessao(response, usuario, settings)
    return UsuarioPublico.model_validate(usuario)
