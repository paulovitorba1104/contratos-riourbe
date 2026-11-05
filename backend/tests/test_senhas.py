import re

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.core.security import gerar_senha_temporaria, validar_politica_senha, verificar_senha
from app.models.usuario import Usuario
from app.schemas.auth import TrocarSenhaRequest
from app.schemas.usuario import SolicitacaoCadastro
from app.services.senhas import aplicar_nova_senha, aplicar_senha_temporaria


def _usuario() -> Usuario:
    return Usuario(nome="Fulano de Tal", matricula="12345", cpf="52998224725", email="f@riourbe.rj.gov.br",
                   senha_hash="x", ativo=True, trocar_senha_obrigatorio=False)


def test_senha_temporaria_respeita_politica_e_formato():
    for _ in range(50):
        senha = gerar_senha_temporaria()
        validar_politica_senha(senha)
        assert re.fullmatch(r"[A-Za-z2-9]{4}-[A-Za-z2-9]{4}-[A-Za-z2-9]{4}", senha)
        assert not set(senha) & set("0O1lI")


def test_senhas_temporarias_nao_se_repetem():
    assert len({gerar_senha_temporaria() for _ in range(200)}) == 200


def test_senha_temporaria_obriga_troca_e_derruba_sessoes():
    usuario = _usuario()
    senha = aplicar_senha_temporaria(usuario)
    assert verificar_senha(senha, usuario.senha_hash)
    assert usuario.trocar_senha_obrigatorio is True
    assert usuario.sessoes_validas_apos is not None


def test_nova_senha_libera_o_acesso():
    usuario = _usuario()
    aplicar_senha_temporaria(usuario)
    aplicar_nova_senha(usuario, "Nova#Senha2026")
    assert verificar_senha("Nova#Senha2026", usuario.senha_hash)
    assert usuario.trocar_senha_obrigatorio is False


def test_api_bloqueada_enquanto_troca_pendente():
    usuario = _usuario()
    usuario.trocar_senha_obrigatorio = True
    with pytest.raises(HTTPException) as exc:
        get_current_user(usuario=usuario)
    assert exc.value.status_code == 403

    usuario.trocar_senha_obrigatorio = False
    assert get_current_user(usuario=usuario) is usuario


def test_troca_recusa_senha_fraca_com_422_e_nao_500():
    with pytest.raises(ValidationError):
        TrocarSenhaRequest(senha_atual="Atual#Senha2026", nova_senha="curta")


def test_troca_recusa_nova_igual_a_atual():
    with pytest.raises(ValidationError):
        TrocarSenhaRequest(senha_atual="Mesma#Senha2026", nova_senha="Mesma#Senha2026")


def test_cadastro_de_usuario_com_senha_fraca_vira_erro_de_validacao():
    with pytest.raises(ValidationError):
        SolicitacaoCadastro(
            nome="Fulano", matricula="123", cpf="52998224725", email="f@riourbe.rj.gov.br", senha="12345678"
        )
