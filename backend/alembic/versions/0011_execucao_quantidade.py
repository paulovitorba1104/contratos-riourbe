"""Controle de contrato por quantidade de execuções (dispensa sazonal, ex.:
limpeza de carpete) como alternativa ao controle por vigência de datas

Revision ID: 0011_execucao_quantidade
Revises: 0010_reajuste_e_anexos
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_execucao_quantidade"
down_revision: Union[str, None] = "0010_reajuste_e_anexos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    modo_execucao = postgresql.ENUM("por_vigencia", "por_quantidade", name="modo_execucao", schema="contratos")
    modo_execucao.create(op.get_bind())

    op.add_column(
        "contratos",
        sa.Column(
            "modo_execucao",
            postgresql.ENUM(
                "por_vigencia", "por_quantidade", name="modo_execucao", schema="contratos", create_type=False
            ),
            nullable=False,
            server_default="por_vigencia",
        ),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("quantidade_execucoes_previstas", sa.Integer(), nullable=True),
        schema="contratos",
    )

    op.create_table(
        "execucoes_contrato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("data_execucao", sa.Date(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("registrado_por_id", sa.Uuid(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["contratos.contratos.id"], name="fk_execucoes_contrato_contrato", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["registrado_por_id"], ["core.usuarios.id"], name="fk_execucoes_contrato_usuario"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_execucoes_contrato_contrato_id",
        "execucoes_contrato",
        ["contrato_id"],
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_index("ix_contratos_execucoes_contrato_contrato_id", table_name="execucoes_contrato", schema="contratos")
    op.drop_table("execucoes_contrato", schema="contratos")

    op.drop_column("contratos", "quantidade_execucoes_previstas", schema="contratos")
    op.drop_column("contratos", "modo_execucao", schema="contratos")
    postgresql.ENUM(name="modo_execucao", schema="contratos").drop(op.get_bind())
