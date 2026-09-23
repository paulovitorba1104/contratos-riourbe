from datetime import date
from decimal import Decimal

from app.services import reajuste as regras
from app.services.relatorio_reajuste import (
    _formatar_competencia,
    _formatar_data_br,
    _formatar_moeda,
    gerar_pdf_distribuicao_reajuste,
)


def test_formatar_moeda_usa_separador_brasileiro():
    assert _formatar_moeda(Decimal("1472983.22")) == "R$ 1.472.983,22"
    assert _formatar_moeda(Decimal("51337.22")) == "R$ 51.337,22"


def test_formatar_data_br():
    assert _formatar_data_br(date(2024, 6, 14)) == "14/06/2024"


def test_formatar_competencia():
    assert _formatar_competencia(date(2024, 6, 1)) == "jun/24"
    assert _formatar_competencia(date(2027, 1, 1)) == "jan/27"


def test_gerar_pdf_distribuicao_reajuste_produz_pdf_valido():
    # Mesmos dados da planilha real usada em test_reajuste.py — marco em
    # 14/06 (pro-rata do primeiro mês) e fim em 13/06 (pro-rata do último).
    distribuicao = regras.calcular_distribuicao_reajuste(
        Decimal("118470.50"),
        Decimal("7169.264543"),
        Decimal("6500.00"),
        date(2026, 6, 14),
        date(2027, 6, 13),
    )

    pdf = gerar_pdf_distribuicao_reajuste(
        numero_contrato="011/2022",
        fornecedor_razao_social="Empresa Teste LTDA",
        indice_nome="IPCA-E",
        data_inicio=date(2026, 6, 14),
        data_fim=date(2027, 6, 13),
        distribuicao=distribuicao,
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_gerar_pdf_distribuicao_reajuste_com_data_formalizacao_e_publicacao():
    distribuicao = regras.calcular_distribuicao_reajuste(
        Decimal("118470.50"),
        Decimal("7169.264543"),
        Decimal("6500.00"),
        date(2026, 6, 14),
        date(2027, 6, 13),
    )

    pdf = gerar_pdf_distribuicao_reajuste(
        numero_contrato="011/2022",
        fornecedor_razao_social="Empresa Teste LTDA",
        indice_nome="IPCA-E",
        data_inicio=date(2026, 6, 14),
        data_fim=date(2027, 6, 13),
        distribuicao=distribuicao,
        data_formalizacao=date(2026, 7, 1),
        data_publicacao=date(2026, 7, 5),
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_gerar_pdf_distribuicao_reajuste_periodo_sem_pro_rata():
    # Marco no dia 1 e fim no último dia do mês comercial — nenhuma nota de
    # rodapé de pro-rata deve ser necessária; só confirma que não quebra.
    distribuicao = regras.calcular_distribuicao_reajuste(
        Decimal("1000.00"), Decimal("110"), Decimal("100"), date(2024, 1, 1), date(2024, 3, 30)
    )

    pdf = gerar_pdf_distribuicao_reajuste(
        numero_contrato="001/2024",
        fornecedor_razao_social="Empresa Teste LTDA",
        indice_nome="IPCA-E",
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 3, 30),
        distribuicao=distribuicao,
    )

    assert pdf.startswith(b"%PDF")
