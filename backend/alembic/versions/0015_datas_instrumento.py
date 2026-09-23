"""Instrumento processual ganha data_formalizacao e data_publicacao — datas
do próprio documento (quando foi assinado/formalizado, quando saiu
publicado, ex. Diário Oficial), preenchidas à mão conforme o processo
avança. Não confundir com criado_em (só quando alguém cadastrou no
sistema) nem com sub_status (etapa de tramitação) — são fatos
independentes.

Revision ID: 0015_datas_instrumento
Revises: 0014_categoria_despesa_fatura
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015_datas_instrumento"
down_revision: Union[str, None] = "0014_categoria_despesa_fatura"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "instrumentos_processuais",
        sa.Column("data_formalizacao", sa.Date(), nullable=True),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("data_publicacao", sa.Date(), nullable=True),
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_column("instrumentos_processuais", "data_publicacao", schema="contratos")
    op.drop_column("instrumentos_processuais", "data_formalizacao", schema="contratos")
