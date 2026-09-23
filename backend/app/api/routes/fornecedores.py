import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.core.cnpj_lookup import consultar_cnpj
from app.core.validadores import cnpj_valido, normalizar_cnpj
from app.db.session import get_db
from app.models.fornecedor import Fornecedor
from app.models.usuario import Usuario
from app.schemas.fornecedor import ConsultaCnpjSaida, FornecedorAtualizar, FornecedorCriar, FornecedorSaida

router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])


def _verificar_cnpj_ativo(cnpj: str) -> None:
    resultado = consultar_cnpj(cnpj)
    situacao = resultado["situacao_cadastral"] if resultado else None
    if situacao is not None and situacao.strip().upper() != "ATIVA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"CNPJ está com situação cadastral '{situacao}' na Receita Federal — "
                "só é possível cadastrar CNPJ ativo."
            ),
        )


@router.get("", response_model=list[FornecedorSaida])
def listar_fornecedores(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[Fornecedor]:
    return db.query(Fornecedor).order_by(Fornecedor.razao_social).all()


@router.get("/consulta-cnpj/{cnpj}", response_model=ConsultaCnpjSaida)
def consultar_cnpj_receita(
    cnpj: str,
    _: Usuario = Depends(get_current_user),
) -> ConsultaCnpjSaida:
    """Prévia ao vivo (enquanto o CNPJ é digitado) — autopreenche a razão
    social e mostra a situação cadastral antes de salvar. Nunca bloqueia:
    CNPJ com formato inválido ou consulta indisponível só volta
    `encontrado=False`, a verificação que de fato recusa o cadastro é a de
    "CNPJ ativo" ao salvar (`_verificar_cnpj_ativo`)."""
    if not cnpj_valido(cnpj):
        return ConsultaCnpjSaida(encontrado=False)
    resultado = consultar_cnpj(normalizar_cnpj(cnpj))
    if resultado is None:
        return ConsultaCnpjSaida(encontrado=False)
    situacao = resultado["situacao_cadastral"]
    return ConsultaCnpjSaida(
        encontrado=True,
        razao_social=resultado["razao_social"],
        situacao_cadastral=situacao,
        ativo=situacao is not None and situacao.strip().upper() == "ATIVA",
    )


@router.post("", response_model=FornecedorSaida, status_code=status.HTTP_201_CREATED)
def criar_fornecedor(
    dados: FornecedorCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Fornecedor:
    _verificar_cnpj_ativo(dados.cnpj)
    fornecedor = Fornecedor(razao_social=dados.razao_social, cnpj=dados.cnpj)
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@router.patch("/{fornecedor_id}", response_model=FornecedorSaida)
def atualizar_fornecedor(
    fornecedor_id: uuid.UUID,
    dados: FornecedorAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Fornecedor:
    fornecedor = db.get(Fornecedor, fornecedor_id)
    if fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")

    dados_informados = dados.model_dump(exclude_unset=True)
    if "cnpj" in dados_informados:
        _verificar_cnpj_ativo(dados_informados["cnpj"])

    for campo, valor in dados_informados.items():
        setattr(fornecedor, campo, valor)

    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@router.delete("/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_fornecedor(
    fornecedor_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador; se o fornecedor já
    # estiver vinculado a algum contrato, o banco recusa (chave estrangeira)
    # e o handler global devolve 409.
    _: Usuario = Depends(exigir_administrador),
) -> None:
    fornecedor = db.get(Fornecedor, fornecedor_id)
    if fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
    db.delete(fornecedor)
    db.commit()
