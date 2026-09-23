"""Fatura ganha categoria_despesa — na imensa maioria PRINCIPAL (o serviço/
objeto do contrato). Em locação de imóvel com fornecedor adicional
administrando o condomínio, a fatura dele costuma somar taxa condominial +
água/luz + taxa de incêndio numa cobrança só; categorizar cada fatura
permite acompanhar a taxa condominial (normalmente fixa) separada do que é
genuinamente variável.

Revision ID: 0014_categoria_despesa_fatura
Revises: 0013_exige_garantia
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_categoria_despesa_fatura"
down_revision: Union[str, None] = "0013_exige_garantia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALORES = ["principal", "condominio", "agua_luz", "taxa_incendio", "outra"]


def upgrade() -> None:
    categoria_despesa = postgresql.ENUM(*VALORES, name="categoria_despesa_fatura", schema="faturas")
    categoria_despesa.create(op.get_bind())

    op.add_column(
        "faturas",
        sa.Column(
            "categoria_despesa",
            postgresql.ENUM(*VALORES, name="categoria_despesa_fatura", schema="faturas", create_type=False),
            nullable=False,
            server_default="principal",
        ),
        schema="faturas",
    )


def downgrade() -> None:
    op.drop_column("faturas", "categoria_despesa", schema="faturas")
    postgresql.ENUM(name="categoria_despesa_fatura", schema="faturas").drop(op.get_bind(), checkfirst=True)
