import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import fornecedores as rota_fornecedores
from app.schemas.fornecedor import FornecedorAtualizar, FornecedorCriar

CNPJ_VALIDO = "11.222.333/0001-81"


def test_fornecedor_normaliza_cnpj_valido():
    fornecedor = FornecedorCriar(razao_social="Empresa X", cnpj=CNPJ_VALIDO)
    assert fornecedor.cnpj == "11222333000181"


def test_fornecedor_rejeita_cnpj_invalido():
    with pytest.raises(ValidationError):
        FornecedorCriar(razao_social="Empresa X", cnpj="11.111.111/1111-11")


def test_fornecedor_atualizar_aceita_campos_parciais():
    dados = FornecedorAtualizar(razao_social="Novo nome")
    assert dados.model_dump(exclude_unset=True) == {"razao_social": "Novo nome"}


def test_fornecedor_atualizar_normaliza_cnpj():
    dados = FornecedorAtualizar(cnpj=CNPJ_VALIDO)
    assert dados.cnpj == "11222333000181"


def test_fornecedor_atualizar_rejeita_cnpj_invalido():
    with pytest.raises(ValidationError):
        FornecedorAtualizar(cnpj="11.111.111/1111-11")


def test_verificar_cnpj_ativo_aceita_quando_situacao_e_ativa(monkeypatch):
    monkeypatch.setattr(rota_fornecedores, "consultar_situacao_cnpj", lambda cnpj: "ATIVA")
    rota_fornecedores._verificar_cnpj_ativo("11222333000181")


def test_verificar_cnpj_ativo_aceita_quando_consulta_indisponivel(monkeypatch):
    monkeypatch.setattr(rota_fornecedores, "consultar_situacao_cnpj", lambda cnpj: None)
    rota_fornecedores._verificar_cnpj_ativo("11222333000181")


def test_verificar_cnpj_ativo_bloqueia_quando_situacao_nao_e_ativa(monkeypatch):
    monkeypatch.setattr(rota_fornecedores, "consultar_situacao_cnpj", lambda cnpj: "BAIXADA")
    with pytest.raises(HTTPException) as exc_info:
        rota_fornecedores._verificar_cnpj_ativo("11222333000181")
    assert exc_info.value.status_code == 422
