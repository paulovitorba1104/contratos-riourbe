"""Gera o PDF "Distribuição do Apostilamento" — mesmo formato da planilha de
controle que a Gerência de Contratos já usa, agora emitido direto do sistema
a partir dos dados de reajuste já salvos no instrumento processual (nunca
recalcula com números diferentes dos que foram registrados)."""

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.reajuste import DIAS_MES_COMERCIAL, DistribuicaoReajuste

NOME_EMPRESA = "Empresa Municipal de Urbanização - Rio-Urbe"
NOME_SETOR = "Gerência de Contratos"

MESES_ABREVIADOS = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


def _formatar_moeda(valor: Decimal) -> str:
    inteiro, _, centavos = f"{valor:,.2f}".partition(".")
    inteiro_pt = inteiro.replace(",", ".")
    return f"R$ {inteiro_pt},{centavos}"


def _formatar_data_br(data: date) -> str:
    return data.strftime("%d/%m/%Y")


def _formatar_competencia(data: date) -> str:
    return f"{MESES_ABREVIADOS[data.month - 1]}/{data.strftime('%y')}"


def gerar_pdf_distribuicao_reajuste(
    *,
    numero_contrato: str,
    fornecedor_razao_social: str,
    indice_nome: str,
    data_inicio: date,
    data_fim: date,
    distribuicao: DistribuicaoReajuste,
) -> bytes:
    """Monta o PDF da distribuição do apostilamento — cabeçalho institucional,
    período do reajuste, tabela mês a mês (mesmas colunas e ordem da planilha
    de controle: mês, valor reajustado, valor antigo, diferença mensal) e a
    linha de totais. Marca com nota de rodapé os meses pro-rata (o primeiro,
    quando o marco cai no meio do mês; o último, quando o período termina
    antes do fim do mês comercial de 30 dias)."""
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )

    estilos = getSampleStyleSheet()
    estilo_empresa = ParagraphStyle("Empresa", parent=estilos["Normal"], fontName="Helvetica-Bold", fontSize=11)
    estilo_setor = ParagraphStyle("Setor", parent=estilos["Normal"], fontSize=10)
    estilo_titulo = ParagraphStyle(
        "Titulo", parent=estilos["Normal"], fontName="Helvetica-Bold", fontSize=12, alignment=1, spaceBefore=10, spaceAfter=10
    )
    estilo_info = ParagraphStyle("Info", parent=estilos["Normal"], fontSize=9, spaceAfter=2)
    estilo_nota = ParagraphStyle("Nota", parent=estilos["Normal"], fontSize=8, textColor=colors.grey, spaceBefore=2)

    elementos = [
        Paragraph(NOME_EMPRESA, estilo_empresa),
        Paragraph(NOME_SETOR, estilo_setor),
        Paragraph("Distribuição do Apostilamento", estilo_titulo),
        Paragraph(f"<b>Contrato:</b> {numero_contrato}", estilo_info),
        Paragraph(f"<b>Fornecedor:</b> {fornecedor_razao_social}", estilo_info),
        Paragraph(f"<b>Índice:</b> {indice_nome}", estilo_info),
        Paragraph(f"<b>Início do Reajuste:</b> A partir de {_formatar_data_br(data_inicio)}", estilo_info),
        Paragraph(f"<b>Final do Reajuste:</b> {_formatar_data_br(data_fim)}", estilo_info),
        Spacer(1, 0.4 * cm),
    ]

    cabecalho = ["MÊS", "Valor Reajustado", "Valor antigo", "Diferença Mensal"]
    linhas_tabela = [cabecalho]

    marcadores: dict[int, str] = {}
    total_linhas = len(distribuicao.linhas)
    for indice, linha in enumerate(distribuicao.linhas):
        competencia = _formatar_competencia(linha.competencia)
        eh_primeira = indice == 0
        eh_ultima = indice == total_linhas - 1

        if eh_primeira and data_inicio.day != 1:
            competencia += "*"
            marcadores["primeira"] = _formatar_competencia(linha.competencia)
        if eh_ultima and data_fim.day != DIAS_MES_COMERCIAL and not eh_primeira:
            competencia += "**"
            marcadores["ultima"] = _formatar_competencia(linha.competencia)

        linhas_tabela.append(
            [
                competencia,
                _formatar_moeda(linha.valor_reajustado),
                _formatar_moeda(linha.valor_antigo),
                _formatar_moeda(linha.diferenca),
            ]
        )

    linhas_tabela.append(
        [
            "TOTAL",
            _formatar_moeda(distribuicao.valor_total_reajustado),
            _formatar_moeda(distribuicao.valor_total_antigo),
            _formatar_moeda(distribuicao.valor_total_apostilamento),
        ]
    )

    tabela = Table(linhas_tabela, colWidths=[3 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm], repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8eef4")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabela)

    if "primeira" in marcadores:
        elementos.append(
            Paragraph(f"*Competência de {marcadores['primeira']} - calculado pro rata.", estilo_nota)
        )
    if "ultima" in marcadores:
        dias = data_fim.day
        elementos.append(
            Paragraph(
                f"**Competência de {marcadores['ultima']} - pro rata de {dias} dias, "
                "correspondente ao fim deste período de reajuste.",
                estilo_nota,
            )
        )

    documento.build(elementos)
    return buffer.getvalue()
