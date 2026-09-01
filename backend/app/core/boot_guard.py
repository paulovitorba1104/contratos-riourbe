"""Guarda de boot: recusa subir em produção com configuração insegura.

Ver seção 13 do plano de desenvolvimento (Infraestrutura de segurança).
"""

from app.core.config import DEFAULT_DEV_ADMIN_PASSWORD, DEFAULT_DEV_JWT_SECRET, Settings


def validar_configuracao_producao(settings: Settings) -> None:
    if not settings.is_producao:
        return

    if settings.jwt_secret == DEFAULT_DEV_JWT_SECRET or len(settings.jwt_secret) < 32:
        raise ValueError(
            "JWT_SECRET inválido para produção: defina um valor com no mínimo 32 caracteres, "
            "diferente do padrão de desenvolvimento."
        )

    if settings.admin_inicial_senha == DEFAULT_DEV_ADMIN_PASSWORD:
        raise ValueError(
            "ADMIN_INICIAL_SENHA inválida para produção: defina uma senha diferente da senha "
            "padrão publicada."
        )

    if not settings.cookie_secure:
        raise ValueError("COOKIE_SECURE deve ser 'true' em produção.")
