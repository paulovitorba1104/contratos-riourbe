"""Cria o administrador inicial, se ainda não existir. Uso: python -m scripts.seed_admin"""

from app.core.config import get_settings
from app.core.security import hash_senha, validar_politica_senha
from app.db.session import SessionLocal
from app.models.usuario import PapelUsuario, Usuario


def seed_admin() -> None:
    settings = get_settings()
    validar_politica_senha(settings.admin_inicial_senha)

    db = SessionLocal()
    try:
        existente = db.query(Usuario).filter(Usuario.matricula == settings.admin_inicial_matricula).first()
        if existente is not None:
            print(f"Administrador '{settings.admin_inicial_matricula}' já existe — nada a fazer.")
            return

        admin = Usuario(
            nome="Administrador Rio-Urbe",
            matricula=settings.admin_inicial_matricula,
            cpf="00000000000",
            email="admin@riourbe.local",
            senha_hash=hash_senha(settings.admin_inicial_senha),
            papel=PapelUsuario.ADMINISTRADOR,
        )
        db.add(admin)
        db.commit()
        print(f"Administrador inicial '{settings.admin_inicial_matricula}' criado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
