"""Autenticação, hashing de senha, JWT e validação de identificador de login.

Ver seção 13 do plano de desenvolvimento (Autenticação e sessão / Política de senha).
"""

import re
import time
from datetime import UTC, datetime, timedelta
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash descartável pré-computado para manter tempo constante quando o usuário não existe.
_HASH_FANTASMA = _pwd_context.hash("hash-fantasma-tempo-constante-login")

SENHAS_PROIBIDAS = {
    "12345678",
    "123456789",
    "1234567890",
    "senha123",
    "senha1234",
    "password",
    "password1",
    "qwertyuiop",
    "administrador",
    "riourbe123",
    "trocarsenha",
}


class TipoIdentificador(str, Enum):
    MATRICULA = "matricula"
    CPF = "cpf"


def detectar_tipo_identificador(identificador: str) -> TipoIdentificador:
    """Detecta se o identificador informado no login é um CPF ou uma matrícula funcional."""
    somente_digitos = re.sub(r"\D", "", identificador)
    if len(somente_digitos) == 11:
        return TipoIdentificador.CPF
    return TipoIdentificador.MATRICULA


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


def cpf_valido(cpf: str) -> bool:
    """Valida CPF pelo algoritmo de dígito verificador (módulo 11)."""
    digitos = normalizar_cpf(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    def _dv(parcial: str) -> str:
        soma = sum(int(d) * peso for d, peso in zip(parcial, range(len(parcial) + 1, 1, -1)))
        resto = (soma * 10) % 11
        return "0" if resto == 10 else str(resto)

    dv1 = _dv(digitos[:9])
    dv2 = _dv(digitos[:9] + dv1)
    return digitos[-2:] == dv1 + dv2


class SenhaInvalida(Exception):
    def __init__(self, motivos: list[str]):
        self.motivos = motivos
        super().__init__("; ".join(motivos))


def validar_politica_senha(senha: str) -> None:
    """Mínimo 10 caracteres, teto de 72 bytes UTF-8, >=3 de 4 classes, sem senhas óbvias."""
    motivos: list[str] = []

    if len(senha) < 10:
        motivos.append("A senha deve ter no mínimo 10 caracteres.")

    if len(senha.encode("utf-8")) > 72:
        motivos.append("A senha deve ter no máximo 72 bytes (limite do bcrypt).")

    if senha.lower() in SENHAS_PROIBIDAS:
        motivos.append("Senha muito comum, escolha outra.")

    classes = 0
    if re.search(r"[a-z]", senha):
        classes += 1
    if re.search(r"[A-Z]", senha):
        classes += 1
    if re.search(r"\d", senha):
        classes += 1
    if re.search(r"[^a-zA-Z0-9]", senha):
        classes += 1
    if classes < 3:
        motivos.append("A senha deve conter ao menos 3 dos 4 tipos: minúscula, maiúscula, dígito, símbolo.")

    if motivos:
        raise SenhaInvalida(motivos)


def hash_senha(senha: str) -> str:
    return _pwd_context.hash(senha[:72].encode("utf-8", errors="ignore").decode("utf-8", errors="ignore"))


def verificar_senha(senha_texto: str, senha_hash: str | None) -> bool:
    """Se senha_hash for None (usuário inexistente), compara contra hash fantasma
    para manter tempo constante e nunca vazar se o usuário existe."""
    alvo = senha_hash or _HASH_FANTASMA
    valido = _pwd_context.verify(senha_texto, alvo)
    return valido and senha_hash is not None


def criar_token_acesso(sub: str, settings: Settings) -> tuple[str, datetime]:
    agora = datetime.now(UTC)
    expira_em = agora + timedelta(hours=settings.jwt_expira_horas)
    payload = {
        "sub": sub,
        "iat": int(agora.timestamp()),
        "exp": int(expira_em.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expira_em


class TokenInvalido(Exception):
    pass


def decodificar_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenInvalido(str(exc)) from exc
    return payload


def token_emitido_apos_corte(iat: int, sessoes_validas_apos: datetime | None) -> bool:
    """Rejeita tokens emitidos antes do corte de revogação (logout / troca de senha)."""
    if sessoes_validas_apos is None:
        return True
    corte = int(sessoes_validas_apos.replace(tzinfo=UTC).timestamp())
    return iat >= corte


def timestamp_atual() -> float:
    return time.time()
