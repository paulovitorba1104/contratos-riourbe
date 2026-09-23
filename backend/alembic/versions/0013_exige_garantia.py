"""Contrato ganha exige_garantia — nem todo contrato precisa de garantia
contratual (ex.: valor baixo dispensado por lei). Falso remove o card de
garantia da urgência de alerta, mas continua permitindo registrar caso o
usuário queira mesmo assim.

Revision ID: 0013_exige_garantia
Revises: 0012_valor_mensal_e_fornecedores
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_exige_garantia"
down_revision = "0012_valor_mensal_e_fornecedores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("exige_garantia", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_column("contratos", "exige_garantia", schema="contratos")
