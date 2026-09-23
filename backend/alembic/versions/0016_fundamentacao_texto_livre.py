"""Fundamentação do instrumento processual vira texto livre — antes era um
enum fixo de duas leis (13.303/16 e 14.133/21) mais um campo de artigo
separado, mas o processo às vezes é fundamentado num decreto, portaria ou
outro ato normativo que não cabia nesse enum. Um único campo de texto
(`fundamentacao`) substitui `fundamentacao_lei` + `fundamentacao_artigo`,
concatenando os dois na migração de dados existentes.

Revision ID: 0016_fundamentacao_texto_livre
Revises: 0015_datas_instrumento
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016_fundamentacao_texto_livre"
down_revision: Union[str, None] = "0015_datas_instrumento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROTULOS_LEI = {
    "lei_13303_16": "Lei 13.303/16",
    "lei_14133_21": "Lei 14.133/21",
}


def upgrade() -> None:
    op.add_column(
        "instrumentos_processuais",
        sa.Column("fundamentacao", sa.String(length=300), nullable=True),
        schema="contratos",
    )

    conexao = op.get_bind()
    for valor_enum, rotulo in ROTULOS_LEI.items():
        conexao.execute(
            sa.text(
                """
                UPDATE contratos.instrumentos_processuais
                SET fundamentacao = :rotulo || ', ' || fundamentacao_artigo
                WHERE fundamentacao_lei = :valor_enum
                """
            ),
            {"rotulo": rotulo, "valor_enum": valor_enum},
        )

    op.alter_column("instrumentos_processuais", "fundamentacao", nullable=False, schema="contratos")

    op.drop_column("instrumentos_processuais", "fundamentacao_artigo", schema="contratos")
    op.drop_column("instrumentos_processuais", "fundamentacao_lei", schema="contratos")
    postgresql.ENUM(name="fundamentacao_lei", schema="contratos").drop(op.get_bind())


def downgrade() -> None:
    # Downgrade sem tentar separar de volta lei/artigo do texto livre — não
    # há como fazer isso de forma confiável. Recria as colunas antigas
    # vazias (lei default 13.303/16, artigo com o texto completo) só para a
    # migração ser reversível estruturalmente.
    fundamentacao_lei = postgresql.ENUM("lei_13303_16", "lei_14133_21", name="fundamentacao_lei", schema="contratos")
    fundamentacao_lei.create(op.get_bind())

    op.add_column(
        "instrumentos_processuais",
        sa.Column(
            "fundamentacao_lei",
            postgresql.ENUM(
                "lei_13303_16", "lei_14133_21", name="fundamentacao_lei", schema="contratos", create_type=False
            ),
            nullable=False,
            server_default="lei_13303_16",
        ),
        schema="contratos",
    )
    op.add_column(
        "instrumentos_processuais",
        sa.Column("fundamentacao_artigo", sa.String(length=100), nullable=False, server_default=""),
        schema="contratos",
    )
    conexao = op.get_bind()
    conexao.execute(
        sa.text(
            "UPDATE contratos.instrumentos_processuais SET fundamentacao_artigo = left(fundamentacao, 100)"
        )
    )
    op.alter_column("instrumentos_processuais", "fundamentacao_lei", server_default=None, schema="contratos")
    op.alter_column("instrumentos_processuais", "fundamentacao_artigo", server_default=None, schema="contratos")
    op.drop_column("instrumentos_processuais", "fundamentacao", schema="contratos")
