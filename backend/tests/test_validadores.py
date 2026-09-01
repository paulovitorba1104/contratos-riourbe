from app.core.validadores import cnpj_valido


def test_cnpj_valido_aceita_cnpj_correto():
    assert cnpj_valido("11.222.333/0001-81")


def test_cnpj_valido_rejeita_digitos_repetidos():
    assert not cnpj_valido("11.111.111/1111-11")


def test_cnpj_valido_rejeita_dv_incorreto():
    assert not cnpj_valido("11.222.333/0001-80")


def test_cnpj_valido_rejeita_tamanho_errado():
    assert not cnpj_valido("123")
