"""Garantia contratual ganha modalidade, valor e o mecanismo de "grande
vulto" — a Lei 13.303/16 (art. 70) limita a garantia a 5% do valor do
contrato (até 10% em contratação de grande vulto com alta complexidade
técnica e riscos financeiros elevados) e prevê 3 modalidades: caução em
dinheiro, seguro-garantia e fiança bancária (art. 70, §1º). Antes só se
registrava as datas da garantia, sem como o sistema checar o limite legal.

Revision ID: 0017_garantia_limite_legal
Revises: 0016_fundamentacao_texto_livre
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_garantia_limite_legal"
down_revision: Union[str, None] = "0016_fundamentacao_texto_livre"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALORES = ["caucao_dinheiro", "seguro_garantia", "fianca_bancaria"]


def upgrade() -> None:
    modalidade_garantia = postgresql.ENUM(*VALORES, name="modalidade_garantia", schema="contratos")
    modalidade_garantia.create(op.get_bind())

    op.add_column(
        "garantias_contrato",
        sa.Column(
            "modalidade",
            postgresql.ENUM(*VALORES, name="modalidade_garantia", schema="contratos", create_type=False),
            nullable=True,
        ),
        schema="contratos",
    )
    op.add_column(
        "garantias_contrato",
        sa.Column("valor_garantia", sa.Numeric(16, 2), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "garantias_contrato",
        sa.Column("grande_vulto", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="contratos",
    )
    op.alter_column("garantias_contrato", "grande_vulto", server_default=None, schema="contratos")
    op.add_column(
        "garantias_contrato",
        sa.Column("grande_vulto_justificativa", sa.Text(), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "garantias_contrato",
        sa.Column("grande_vulto_documento_sei", sa.String(length=50), nullable=True),
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_column("garantias_contrato", "grande_vulto_documento_sei", schema="contratos")
    op.drop_column("garantias_contrato", "grande_vulto_justificativa", schema="contratos")
    op.drop_column("garantias_contrato", "grande_vulto", schema="contratos")
    op.drop_column("garantias_contrato", "valor_garantia", schema="contratos")
    op.drop_column("garantias_contrato", "modalidade", schema="contratos")
    postgresql.ENUM(name="modalidade_garantia", schema="contratos").drop(op.get_bind())
