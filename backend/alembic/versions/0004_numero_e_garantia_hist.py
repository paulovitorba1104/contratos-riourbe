"""Adiciona número do contrato e transforma garantia contratual num
histórico de registros (auditável), em vez de 2 colunas sobrescritas

Revision ID: 0004_numero_contrato_e_garantia_historico
Revises: 0003_fiscais
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004_numero_e_garantia_hist"
down_revision: Union[str, None] = "0003_fiscais"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contratos", sa.Column("numero_contrato", sa.String(length=50), nullable=True), schema="contratos")
    # Backfill: contratos existentes ainda não têm número próprio — usa o
    # processo SEI como valor inicial para não deixar a coluna vazia antes
    # de virar NOT NULL (quem precisar corrige depois, agora que dá para editar).
    op.execute("UPDATE contratos.contratos SET numero_contrato = processo_sei WHERE numero_contrato IS NULL")
    op.alter_column("contratos", "numero_contrato", nullable=False, schema="contratos")

    op.create_table(
        "garantias_contrato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("data_inicio_garantia", sa.Date(), nullable=True),
        sa.Column("data_fim_garantia", sa.Date(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("registrado_por_id", sa.Uuid(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["contratos.contratos.id"], name="fk_garantias_contrato_contrato", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["core.usuarios.id"], name="fk_garantias_contrato_usuario"),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_garantias_contrato_contrato_id",
        "garantias_contrato",
        ["contrato_id"],
        schema="contratos",
    )

    # Sem dados reais de garantia em produção ainda (o único registro de
    # teste foi limpo antes do deploy) — remove as colunas antigas direto,
    # em vez de migrar linha a linha, seguindo o mesmo critério já usado na
    # revisão anterior para contrato_fiscais.
    op.drop_column("contratos", "data_inicio_garantia", schema="contratos")
    op.drop_column("contratos", "data_fim_garantia", schema="contratos")


def downgrade() -> None:
    op.add_column("contratos", sa.Column("data_inicio_garantia", sa.Date(), nullable=True), schema="contratos")
    op.add_column("contratos", sa.Column("data_fim_garantia", sa.Date(), nullable=True), schema="contratos")
    op.drop_index("ix_contratos_garantias_contrato_contrato_id", table_name="garantias_contrato", schema="contratos")
    op.drop_table("garantias_contrato", schema="contratos")
    op.drop_column("contratos", "numero_contrato", schema="contratos")
