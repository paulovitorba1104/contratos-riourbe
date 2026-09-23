"""Contrato cotado por mensalidade (valor global derivado) e fornecedores
adicionais vinculados ao contrato (ex.: locação de imóvel — uma empresa
recebe o aluguel, outra administra o condomínio); fatura pode ser emitida
para qualquer um dos fornecedores do contrato, não só o principal

Revision ID: 0012_valor_mensal_e_fornecedores
Revises: 0011_execucao_quantidade
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_valor_mensal_e_fornecedores"
down_revision: Union[str, None] = "0011_execucao_quantidade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- contratos.contratos: valor mensal x global -------------------------
    modo_valor = postgresql.ENUM("global", "mensal", name="modo_valor_contrato", schema="contratos")
    modo_valor.create(op.get_bind())

    op.add_column(
        "contratos",
        sa.Column(
            "modo_valor",
            postgresql.ENUM("global", "mensal", name="modo_valor_contrato", schema="contratos", create_type=False),
            nullable=False,
            server_default="global",
        ),
        schema="contratos",
    )
    op.add_column("contratos", sa.Column("valor_mensal", sa.Numeric(16, 2), nullable=True), schema="contratos")
    op.add_column("contratos", sa.Column("carencia_meses", sa.Integer(), nullable=True), schema="contratos")

    # --- contratos.fornecedores_adicionais_contrato --------------------------
    op.create_table(
        "fornecedores_adicionais_contrato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("fornecedor_id", sa.Uuid(), nullable=False),
        sa.Column("papel", sa.String(length=100), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["contratos.contratos.id"],
            name="fk_fornecedores_adicionais_contrato_contrato",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"], ["core.fornecedores.id"], name="fk_fornecedores_adicionais_contrato_fornecedor"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_fornecedores_adicionais_contrato_contrato_id",
        "fornecedores_adicionais_contrato",
        ["contrato_id"],
        schema="contratos",
    )

    # --- faturas.faturas: fornecedor por fatura (nulo = principal do contrato)
    op.add_column("faturas", sa.Column("fornecedor_id", sa.Uuid(), nullable=True), schema="faturas")
    op.create_foreign_key(
        "fk_faturas_fornecedor",
        "faturas",
        "fornecedores",
        ["fornecedor_id"],
        ["id"],
        source_schema="faturas",
        referent_schema="core",
    )


def downgrade() -> None:
    op.drop_constraint("fk_faturas_fornecedor", "faturas", schema="faturas", type_="foreignkey")
    op.drop_column("faturas", "fornecedor_id", schema="faturas")

    op.drop_index(
        "ix_contratos_fornecedores_adicionais_contrato_contrato_id",
        table_name="fornecedores_adicionais_contrato",
        schema="contratos",
    )
    op.drop_table("fornecedores_adicionais_contrato", schema="contratos")

    op.drop_column("contratos", "carencia_meses", schema="contratos")
    op.drop_column("contratos", "valor_mensal", schema="contratos")
    op.drop_column("contratos", "modo_valor", schema="contratos")
    postgresql.ENUM(name="modo_valor_contrato", schema="contratos").drop(op.get_bind())
