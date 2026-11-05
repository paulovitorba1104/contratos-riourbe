"""Redefinição de senha sem e-mail. Os dois caminhos (administrador pela API e
script de resgate no servidor) passam por aqui, para terem o mesmo efeito."""

from datetime import UTC, datetime

from app.core.security import gerar_senha_temporaria, hash_senha
from app.models.usuario import Usuario


def aplicar_senha_temporaria(usuario: Usuario) -> str:
    """Troca a senha por uma temporária, derruba as sessões abertas e obriga a
    troca no próximo login. Devolve a senha em texto — mostrar uma única vez."""
    senha = gerar_senha_temporaria()
    usuario.senha_hash = hash_senha(senha)
    usuario.trocar_senha_obrigatorio = True
    usuario.sessoes_validas_apos = datetime.now(UTC)
    return senha


def aplicar_nova_senha(usuario: Usuario, nova_senha: str) -> None:
    """Senha escolhida pelo próprio usuário. Derruba todas as sessões — quem
    chamou precisa emitir um cookie novo para a sessão atual continuar."""
    usuario.senha_hash = hash_senha(nova_senha)
    usuario.trocar_senha_obrigatorio = False
    usuario.sessoes_validas_apos = datetime.now(UTC)
