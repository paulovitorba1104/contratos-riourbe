"""Módulo Faturamento: controle de faturas — medições, registro das notas,
conferência documental e tributária, glosas e linha do tempo de eventos.

É um controle de acompanhamento: a liquidação é ato de outro setor, fora deste
sistema, então não existe etapa de liquidação no fluxo. O que o módulo faz é
registrar o andamento e conferir.

Todas as tabelas ficam no schema `faturas`, já criado na migração inicial. O
contrato ganha `exige_medicao` para marcar obras/serviços continuados, onde a
fatura só é aceita vinculada a uma medição aprovada.

As alíquotas ficam em `faturas.regras_tributarias`, entregue **vazia**: a
configuração fiscal é cadastrada pela tela, para que mudança de legislação seja
mudança de cadastro e não nova versão do sistema.

Revision ID: 0007_faturamento
Revises: 0006_processos_contrato
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_faturamento"
down_revision = "0006_processos_contrato"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("exige_medicao", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="contratos",
    )

    status_medicao = postgresql.ENUM(
        "em_elaboracao", "aprovada", "rejeitada", name="status_medicao", schema="faturas", create_type=False
    )
    status_fatura = postgresql.ENUM(
        "recebida",
        "em_conferencia",
        "conferida",
        "atestada",
        "paga",
        "devolvida",
        "cancelada",
        name="status_fatura",
        schema="faturas",
        create_type=False,
    )
    tipo_evento = postgresql.ENUM(
        "recebimento",
        "conferencia",
        "atesto",
        "pagamento",
        "devolucao",
        "cancelamento",
        name="tipo_evento_fatura",
        schema="faturas",
        create_type=False,
    )
    tributo = postgresql.ENUM(
        "irrf", "inss", "iss", "pis", "cofins", "csll", name="tributo", schema="faturas", create_type=False
    )
    situacao_item = postgresql.ENUM(
        "conforme",
        "nao_conforme",
        "nao_aplicavel",
        name="situacao_item_conferencia",
        schema="faturas",
        create_type=False,
    )
    for tipo_enum in (status_medicao, status_fatura, tipo_evento, tributo, situacao_item):
        tipo_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "medicoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contrato_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contratos.contratos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("numero_medicao", sa.String(50), nullable=False),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("valor_medido", sa.Numeric(16, 2), nullable=False),
        sa.Column("status", status_medicao, nullable=False, server_default="em_elaboracao"),
        sa.Column(
            "aprovado_por_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.usuarios.id"), nullable=True
        ),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )
    op.create_index("ix_medicoes_contrato", "medicoes", ["contrato_id"], schema="faturas")

    op.create_table(
        "faturas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contrato_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contratos.contratos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "medicao_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.medicoes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fatura_origem_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.faturas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("numero_nota_fiscal", sa.String(50), nullable=False),
        sa.Column("serie", sa.String(20), nullable=True),
        sa.Column("numero_processo_sei", sa.String(50), nullable=True),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_recebimento", sa.Date(), nullable=False),
        sa.Column("valor_bruto", sa.Numeric(16, 2), nullable=False),
        sa.Column("status", status_fatura, nullable=False, server_default="recebida"),
        sa.Column("data_vencimento", sa.Date(), nullable=True),
        sa.Column("data_envio_gco", sa.Date(), nullable=True),
        sa.Column("data_liquidacao", sa.Date(), nullable=True),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )
    op.create_index("ix_faturas_contrato", "faturas", ["contrato_id"], schema="faturas")
    op.create_index("ix_faturas_status", "faturas", ["status"], schema="faturas")

    op.create_table(
        "glosas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fatura_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.faturas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("valor", sa.Numeric(16, 2), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "registrado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.usuarios.id"),
            nullable=False,
        ),
        sa.Column("registrado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )
    op.create_index("ix_glosas_fatura", "glosas", ["fatura_id"], schema="faturas")

    op.create_table(
        "regras_tributarias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tributo", tributo, nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("base_legal", sa.String(200), nullable=True),
        sa.Column("aliquota", sa.Numeric(7, 4), nullable=False),
        sa.Column("percentual_base", sa.Numeric(7, 4), nullable=False, server_default="100"),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )

    op.create_table(
        "retencoes_fatura",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fatura_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.faturas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tributo", tributo, nullable=False),
        sa.Column("base_calculo", sa.Numeric(16, 2), nullable=False),
        sa.Column("aliquota", sa.Numeric(7, 4), nullable=False),
        sa.Column("valor_esperado", sa.Numeric(16, 2), nullable=False),
        sa.Column("valor_informado", sa.Numeric(16, 2), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )
    op.create_index("ix_retencoes_fatura", "retencoes_fatura", ["fatura_id"], schema="faturas")

    op.create_table(
        "modelos_checklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )

    op.create_table(
        "itens_modelo_checklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "modelo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.modelos_checklist.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("descricao", sa.String(300), nullable=False),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="faturas",
    )
    op.create_index(
        "ix_itens_modelo_checklist_modelo", "itens_modelo_checklist", ["modelo_id"], schema="faturas"
    )

    op.create_table(
        "conferencias",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fatura_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.faturas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "modelo_checklist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.modelos_checklist.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "conferido_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.usuarios.id"),
            nullable=False,
        ),
        sa.Column("conferido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        schema="faturas",
    )
    op.create_index("ix_conferencias_fatura", "conferencias", ["fatura_id"], schema="faturas")

    op.create_table(
        "itens_conferencia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conferencia_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.conferencias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("descricao", sa.String(300), nullable=False),
        sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("situacao", situacao_item, nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        schema="faturas",
    )
    op.create_index(
        "ix_itens_conferencia_conferencia", "itens_conferencia", ["conferencia_id"], schema="faturas"
    )

    op.create_table(
        "eventos_fatura",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fatura_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("faturas.faturas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", tipo_evento, nullable=False),
        sa.Column("data_evento", sa.Date(), nullable=False),
        sa.Column(
            "responsavel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.usuarios.id"),
            nullable=False,
        ),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="faturas",
    )
    op.create_index("ix_eventos_fatura", "eventos_fatura", ["fatura_id"], schema="faturas")


def downgrade() -> None:
    for tabela in (
        "eventos_fatura",
        "itens_conferencia",
        "conferencias",
        "itens_modelo_checklist",
        "modelos_checklist",
        "retencoes_fatura",
        "regras_tributarias",
        "glosas",
        "faturas",
        "medicoes",
    ):
        op.drop_table(tabela, schema="faturas")

    for nome_enum in (
        "situacao_item_conferencia",
        "tributo",
        "tipo_evento_fatura",
        "status_fatura",
        "status_medicao",
    ):
        postgresql.ENUM(name=nome_enum, schema="faturas").drop(op.get_bind(), checkfirst=True)

    op.drop_column("contratos", "exige_medicao", schema="contratos")
