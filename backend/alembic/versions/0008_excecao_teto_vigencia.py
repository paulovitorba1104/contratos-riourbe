"""Exceção ao teto de 5 anos de vigência (art. 71, I e II, da Lei 13.303/16)

Revision ID: 0008_excecao_teto_vigencia
Revises: 0007_faturamento
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_excecao_teto_vigencia"
down_revision: Union[str, None] = "0007_faturamento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tipo = postgresql.ENUM("art_71_i", "art_71_ii", name="excecao_teto_vigencia", schema="contratos")
    tipo.create(op.get_bind())

    op.add_column(
        "contratos",
        sa.Column(
            "excecao_teto_vigencia",
            postgresql.ENUM("art_71_i", "art_71_ii", name="excecao_teto_vigencia", schema="contratos", create_type=False),
            nullable=True,
        ),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("excecao_teto_justificativa", sa.Text(), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("excecao_teto_documento_sei", sa.String(length=50), nullable=True),
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_column("contratos", "excecao_teto_documento_sei", schema="contratos")
    op.drop_column("contratos", "excecao_teto_justificativa", schema="contratos")
    op.drop_column("contratos", "excecao_teto_vigencia", schema="contratos")
    postgresql.ENUM(name="excecao_teto_vigencia", schema="contratos").drop(op.get_bind())
