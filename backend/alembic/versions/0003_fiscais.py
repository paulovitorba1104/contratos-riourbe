"""Fiscais como cadastro próprio (não usuário do sistema), vínculo temporal
com o contrato, e campo ativo em fornecedores

Revision ID: 0003_fiscais
Revises: 0002_modulo_contratos
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003_fiscais"
down_revision: Union[str, None] = "0002_modulo_contratos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("fornecedores", sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()), schema="core")

    op.create_table(
        "fiscais",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("matricula", sa.String(length=30), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("matricula", name="uq_core_fiscais_matricula"),
        sa.UniqueConstraint("cpf", name="uq_core_fiscais_cpf"),
        schema="core",
    )

    # contrato_fiscais era uma associação simples (contrato_id, usuario_id) —
    # vira um vínculo temporal (fiscal_id, data_inicio, data_fim). Sem dados
    # reais em produção ainda, recria do zero em vez de migrar linha a linha.
    op.drop_table("contrato_fiscais", schema="contratos")
    op.create_table(
        "contrato_fiscais",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_id", sa.Uuid(), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["contratos.contratos.id"], name="fk_contrato_fiscais_contrato", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["fiscal_id"], ["core.fiscais.id"], name="fk_contrato_fiscais_fiscal"),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_contrato_fiscais_contrato_id",
        "contrato_fiscais",
        ["contrato_id"],
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_table("contrato_fiscais", schema="contratos")
    op.create_table(
        "contrato_fiscais",
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["contratos.contratos.id"], name="fk_contrato_fiscais_contrato", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["core.usuarios.id"], name="fk_contrato_fiscais_usuario"),
        sa.PrimaryKeyConstraint("contrato_id", "usuario_id", name="pk_contrato_fiscais"),
        schema="contratos",
    )

    op.drop_table("fiscais", schema="core")
    op.drop_column("fornecedores", "ativo", schema="core")
