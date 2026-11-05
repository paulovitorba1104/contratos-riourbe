from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.deps import exigir_modulo
from app.models.usuario import ModuloSistema, PapelUsuario, SituacaoUsuario, Usuario
from app.schemas.usuario import AcessoUsuario, SolicitacaoCadastro, UsuarioCriar

CPF_VALIDO = "52998224725"


def _usuario(papel=PapelUsuario.OPERADOR, modulos=(), ativo=True, aprovado=True) -> Usuario:
    return Usuario(
        nome="Fulano de Tal",
        matricula="123",
        cpf=CPF_VALIDO,
        email="f@riourbe.rj.gov.br",
        senha_hash="x",
        papel=papel,
        modulos=list(modulos),
        ativo=ativo,
        aprovado_em=datetime.now(UTC) if aprovado else None,
    )


def _checar(dependencia, usuario, metodo="GET"):
    return dependencia(request=SimpleNamespace(method=metodo), usuario=usuario)


def test_administrador_acessa_qualquer_modulo_sem_lista():
    admin = _usuario(papel=PapelUsuario.ADMINISTRADOR)
    assert all(admin.pode_acessar(m) for m in ModuloSistema)


def test_operador_so_acessa_os_modulos_liberados():
    operador = _usuario(modulos=["faturas"])
    assert operador.pode_acessar(ModuloSistema.FATURAS)
    assert not operador.pode_acessar(ModuloSistema.CONTRATOS)


@pytest.mark.parametrize(
    ("ativo", "aprovado", "esperado"),
    [
        (True, False, SituacaoUsuario.PENDENTE),
        (False, False, SituacaoUsuario.RECUSADO),
        (True, True, SituacaoUsuario.ATIVO),
        (False, True, SituacaoUsuario.DESATIVADO),
    ],
)
def test_situacao_do_usuario(ativo, aprovado, esperado):
    assert _usuario(ativo=ativo, aprovado=aprovado).situacao == esperado


def test_rota_do_modulo_bloqueia_operador_sem_o_modulo():
    dependencia = exigir_modulo(ModuloSistema.CONTRATOS)
    with pytest.raises(HTTPException) as exc:
        _checar(dependencia, _usuario(modulos=["faturas"]))
    assert exc.value.status_code == 403
    assert "Contratos" in exc.value.detail
    assert _checar(dependencia, _usuario(modulos=["contratos"]), "POST") is not None


def test_faturas_le_contratos_mas_nao_altera():
    dependencia = exigir_modulo(ModuloSistema.CONTRATOS, leitura_tambem_para=(ModuloSistema.FATURAS,))
    so_faturas = _usuario(modulos=["faturas"])
    assert _checar(dependencia, so_faturas, "GET") is so_faturas
    for metodo in ("POST", "PATCH", "PUT", "DELETE"):
        with pytest.raises(HTTPException):
            _checar(dependencia, so_faturas, metodo)


def test_operador_sem_modulo_nao_le_nada():
    dependencia = exigir_modulo(ModuloSistema.CONTRATOS, leitura_tambem_para=(ModuloSistema.FATURAS,))
    with pytest.raises(HTTPException):
        _checar(dependencia, _usuario(modulos=[]))


def test_pedido_de_cadastro_valida_os_dados():
    pedido = SolicitacaoCadastro(
        nome="  Maria Souza ", matricula=" 12/345.678-9 ", cpf="529.982.247-25", email="m@x.com", senha="Senha#Forte2026"
    )
    assert pedido.nome == "Maria Souza"
    assert pedido.matricula == "12/345.678-9"
    assert pedido.cpf == CPF_VALIDO

    with pytest.raises(ValidationError):
        SolicitacaoCadastro(nome="Maria", matricula="   ", cpf=CPF_VALIDO, email="m@x.com", senha="Senha#Forte2026")
    with pytest.raises(ValidationError):
        SolicitacaoCadastro(nome="Maria", matricula="1", cpf="11111111111", email="m@x.com", senha="Senha#Forte2026")


def test_pedido_de_cadastro_nao_escolhe_papel_nem_modulo():
    pedido = SolicitacaoCadastro.model_validate(
        {"nome": "Maria", "matricula": "1", "cpf": CPF_VALIDO, "email": "m@x.com", "senha": "Senha#Forte2026",
         "papel": "administrador", "modulos": ["contratos"]}
    )
    assert not hasattr(pedido, "papel")
    assert not hasattr(pedido, "modulos")


def test_acesso_remove_repeticao_e_recusa_modulo_inexistente():
    assert AcessoUsuario(modulos=["faturas", "faturas", "contratos"]).modulos == [
        ModuloSistema.FATURAS,
        ModuloSistema.CONTRATOS,
    ]
    with pytest.raises(ValidationError):
        AcessoUsuario(modulos=["almoxarifado-que-nao-existe"])


def test_cadastro_pelo_administrador_nao_recebe_senha():
    usuario = UsuarioCriar(nome="Maria", matricula="1", cpf=CPF_VALIDO, email="m@x.com", papel="operador",
                           modulos=["contratos"])
    assert "senha" not in UsuarioCriar.model_fields
    assert usuario.modulos == [ModuloSistema.CONTRATOS]
