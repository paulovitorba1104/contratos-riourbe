"""Reajuste (classificação do contrato + cálculo persistido no instrumento
de apostilamento) e anexos de arquivo por instrumento processual

Revision ID: 0010_reajuste_e_anexos
Revises: 0009_setor_e_valor_historico
Create Date: 2026-09-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_reajuste_e_anexos"
down_revision: Union[str, None] = "0009_setor_e_valor_historico"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- contratos.contratos: classificação de reajuste -------------------
    tipo_reajuste = postgresql.ENUM("automatico", "mediante_solicitacao", name="tipo_reajuste", schema="contratos")
    tipo_reajuste.create(op.get_bind())

    op.add_column(
        "contratos",
        sa.Column(
            "tipo_reajuste",
            postgresql.ENUM(
                "automatico", "mediante_solicitacao", name="tipo_reajuste", schema="contratos", create_type=False
            ),
            nullable=True,
        ),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("periodicidade_reajuste_meses", sa.Integer(), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("indice_reajuste_padrao", sa.String(length=50), nullable=True),
        schema="contratos",
    )

    # --- contratos.instrumentos_processuais: cálculo de reajuste ----------
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_indice_nome", sa.String(length=50), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_indice_atual", sa.Numeric(12, 6), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_indice_base", sa.Numeric(12, 6), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_valor_mensal_antigo", sa.Numeric(16, 2), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_valor_mensal_novo", sa.Numeric(16, 2), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_data_inicio", sa.Date(), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("reajuste_data_fim", sa.Date(), nullable=True),
        schema="contratos",
    )

    # --- contratos.anexos_instrumento --------------------------------------
    op.create_table(
        "anexos_instrumento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrumento_id", sa.Uuid(), nullable=False),
        sa.Column("nome_arquivo", sa.String(length=255), nullable=False),
        sa.Column("caminho_relativo", sa.String(length=500), nullable=False),
        sa.Column("tipo_mime", sa.String(length=100), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("enviado_por_id", sa.Uuid(), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["instrumento_id"],
            ["contratos.instrumentos_processuais.id"],
            name="fk_anexos_instrumento_instrumento",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["enviado_por_id"], ["core.usuarios.id"], name="fk_anexos_instrumento_usuario"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_anexos_instrumento_instrumento_id",
        "anexos_instrumento",
        ["instrumento_id"],
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_index("ix_contratos_anexos_instrumento_instrumento_id", table_name="anexos_instrumento", schema="contratos")
    op.drop_table("anexos_instrumento", schema="contratos")

    for coluna in (
        "reajuste_data_fim",
        "reajuste_data_inicio",
        "reajuste_valor_mensal_novo",
        "reajuste_valor_mensal_antigo",
        "reajuste_indice_base",
        "reajuste_indice_atual",
        "reajuste_indice_nome",
    ):
        op.drop_column("instrumentos_processuais", coluna, schema="contratos")

    op.drop_column("contratos", "indice_reajuste_padrao", schema="contratos")
    op.drop_column("contratos", "periodicidade_reajuste_meses", schema="contratos")
    op.drop_column("contratos", "tipo_reajuste", schema="contratos")
    postgresql.ENUM(name="tipo_reajuste", schema="contratos").drop(op.get_bind())
