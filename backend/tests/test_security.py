import pytest

from app.core.security import (
    TipoIdentificador,
    cpf_valido,
    detectar_tipo_identificador,
    hash_senha,
    validar_politica_senha,
    verificar_senha,
    SenhaInvalida,
)


def test_cpf_valido_aceita_cpf_correto():
    assert cpf_valido("529.982.247-25")


def test_cpf_valido_rejeita_digitos_repetidos():
    assert not cpf_valido("111.111.111-11")


def test_cpf_valido_rejeita_dv_incorreto():
    assert not cpf_valido("529.982.247-24")


def test_detecta_cpf_por_11_digitos():
    assert detectar_tipo_identificador("529.982.247-25") == TipoIdentificador.CPF


def test_detecta_matricula_quando_nao_tem_11_digitos():
    assert detectar_tipo_identificador("12345") == TipoIdentificador.MATRICULA


def test_politica_senha_rejeita_curta():
    with pytest.raises(SenhaInvalida):
        validar_politica_senha("Abc123!")


def test_politica_senha_rejeita_poucas_classes():
    with pytest.raises(SenhaInvalida):
        validar_politica_senha("minusculas")


def test_politica_senha_aceita_senha_forte():
    validar_politica_senha("Senh@Forte2026")


def test_hash_e_verificacao_senha():
    hash_ = hash_senha("Senh@Forte2026")
    assert verificar_senha("Senh@Forte2026", hash_)
    assert not verificar_senha("SenhaErrada", hash_)


def test_verificar_senha_usuario_inexistente_nao_estoura():
    assert not verificar_senha("QualquerSenha123!", None)
