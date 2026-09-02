"""Contrato passa a ter N números de processo (histórico entre SICOP, Processo.Rio
e SEI.Rio), cada um marcado como principal ou apenso — substitui a coluna processo_sei

Revision ID: 0006_processos_contrato
Revises: 0005_ripm_opcional
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0006_processos_contrato"
down_revision: Union[str, None] = "0005_ripm_opcional"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processos_contrato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("numero_processo", sa.String(length=50), nullable=False),
        sa.Column(
            "sistema_origem",
            sa.Enum("sicop", "processo_rio", "sei_rio", name="sistema_processo", schema="contratos"),
            nullable=False,
        ),
        sa.Column(
            "tipo", sa.Enum("principal", "apenso", name="tipo_processo", schema="contratos"), nullable=False
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"], ["contratos.contratos.id"], name="fk_processos_contrato_contrato", ondelete="CASCADE"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_processos_contrato_contrato_id",
        "processos_contrato",
        ["contrato_id"],
        schema="contratos",
    )

    # Migra o único processo_sei de cada contrato existente para um registro
    # "principal" — sem como saber de qual dos 3 sistemas veio cada número
    # antigo, assume sei_rio (o sistema atual) como melhor palpite; quem
    # precisar corrige depois, agora que dá para editar.
    op.execute(
        """
        INSERT INTO contratos.processos_contrato (id, contrato_id, numero_processo, sistema_origem, tipo)
        SELECT gen_random_uuid(), id, processo_sei, 'sei_rio', 'principal'
        FROM contratos.contratos
        """
    )

    op.drop_column("contratos", "processo_sei", schema="contratos")


def downgrade() -> None:
    op.add_column("contratos", sa.Column("processo_sei", sa.String(length=50), nullable=True), schema="contratos")
    op.execute(
        """
        UPDATE contratos.contratos c
        SET processo_sei = p.numero_processo
        FROM contratos.processos_contrato p
        WHERE p.contrato_id = c.id AND p.tipo = 'principal'
        """
    )
    op.alter_column("contratos", "processo_sei", nullable=False, schema="contratos")
    op.drop_index("ix_contratos_processos_contrato_contrato_id", table_name="processos_contrato", schema="contratos")
    op.drop_table("processos_contrato", schema="contratos")
