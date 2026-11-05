"""Redefinição de senha sem e-mail: o administrador (ou o script de resgate no
servidor) gera uma senha temporária, e o usuário fica obrigado a trocá-la no
próximo login. Esta coluna marca esse estado.

Revision ID: 0018_troca_senha_obrigatoria
Revises: 0017_garantia_limite_legal
Create Date: 2026-11-05

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0018_troca_senha_obrigatoria"
down_revision: Union[str, None] = "0017_garantia_limite_legal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("trocar_senha_obrigatorio", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("usuarios", "trocar_senha_obrigatorio", schema="core")
