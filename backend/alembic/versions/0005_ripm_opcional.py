"""RIPM deixa de ser obrigatório no instrumento processual — é um checklist
de apoio administrativo, não um documento jurídico do processo

Revision ID: 0005_ripm_opcional
Revises: 0004_numero_e_garantia_hist
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_ripm_opcional"
down_revision: Union[str, None] = "0004_numero_e_garantia_hist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("instrumentos_processuais", "modelo_ripm_id", nullable=True, schema="contratos")


def downgrade() -> None:
    op.alter_column("instrumentos_processuais", "modelo_ripm_id", nullable=False, schema="contratos")
