"""Resgate de conta sem e-mail, rodado no servidor por quem tem acesso a ele.

Gera uma senha temporária para o usuário (matrícula ou CPF), derruba as sessões
abertas dele e obriga a troca no próximo login. Serve para o caso em que nenhum
administrador consegue entrar (ex.: o único administrador esqueceu a senha).

Uso: python -m scripts.redefinir_senha <matricula-ou-cpf>
"""

import sys

from app.core.security import TipoIdentificador, detectar_tipo_identificador, normalizar_cpf
from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.services.auditoria import registrar_log
from app.services.senhas import aplicar_senha_temporaria


def redefinir(identificador: str) -> int:
    db = SessionLocal()
    try:
        if detectar_tipo_identificador(identificador) == TipoIdentificador.CPF:
            usuario = db.query(Usuario).filter(Usuario.cpf == normalizar_cpf(identificador)).first()
        else:
            usuario = db.query(Usuario).filter(Usuario.matricula == identificador).first()

        if usuario is None:
            print(f"Nenhum usuário com matrícula/CPF '{identificador}'.", file=sys.stderr)
            return 1
        if not usuario.ativo:
            print(f"O usuário '{usuario.nome}' está desativado — nada foi alterado.", file=sys.stderr)
            return 1

        # Lido antes do commit, que expira o objeto e o tornaria ilegível após o close.
        nome = usuario.nome
        senha = aplicar_senha_temporaria(usuario)
        registrar_log(
            db,
            usuario_id=None,
            acao="redefinir_senha_via_servidor",
            entidade="usuario",
            entidade_id=str(usuario.id),
        )
        db.commit()
    finally:
        db.close()

    print(f"Senha temporária de {nome}: {senha}")
    print("Ao entrar com ela, o sistema exige a escolha de uma senha nova antes de liberar o acesso.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m scripts.redefinir_senha <matricula-ou-cpf>", file=sys.stderr)
        sys.exit(2)
    sys.exit(redefinir(sys.argv[1]))
