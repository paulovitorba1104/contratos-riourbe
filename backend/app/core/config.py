from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_JWT_SECRET = "dev-secret-change-me-dev-secret-change-me"
DEFAULT_DEV_ADMIN_PASSWORD = "TrocarSenha#2026"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Rio-Urbe — Gestão de Contratos"
    ambiente: str = "development"  # development | production

    database_url: str = "postgresql+psycopg://riourbe:riourbe@127.0.0.1:5432/riourbe"

    jwt_secret: str = DEFAULT_DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expira_horas: int = 12

    cookie_secure: bool = False
    cookie_name: str = "riourbe_session"

    admin_inicial_matricula: str = "admin"
    admin_inicial_senha: str = DEFAULT_DEV_ADMIN_PASSWORD

    cors_origins: str = "http://localhost:5173"

    brevo_api_key: str | None = None
    brevo_remetente_email: str | None = None

    max_body_size_bytes: int = 1 * 1024 * 1024  # 1 MiB

    @property
    def is_producao(self) -> bool:
        return self.ambiente.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
