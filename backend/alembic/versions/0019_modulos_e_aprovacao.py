"""Controle de acesso por módulo e cadastro com aprovação: o usuário pede acesso
pela tela de login (fica pendente até um administrador aprovar) e o operador só
acessa os módulos que o administrador liberar.

Usuários que já existiam são dados como aprovados, e operadores já existentes
recebem os módulos implementados hoje (Contratos e Faturas) — sem isso, quem já
usava o sistema perderia o acesso no dia da atualização.

Revision ID: 0019_modulos_e_aprovacao
Revises: 0018_troca_senha_obrigatoria
Create Date: 2026-11-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019_modulos_e_aprovacao"
down_revision: Union[str, None] = "0018_troca_senha_obrigatoria"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("modulos", postgresql.ARRAY(sa.String(30)), nullable=False, server_default=sa.text("'{}'")),
        schema="core",
    )
    op.add_column("usuarios", sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True), schema="core")
    op.execute("UPDATE core.usuarios SET aprovado_em = criado_em")
    op.execute("UPDATE core.usuarios SET modulos = ARRAY['contratos', 'faturas'] WHERE papel = 'operador'")


def downgrade() -> None:
    op.drop_column("usuarios", "aprovado_em", schema="core")
    op.drop_column("usuarios", "modulos", schema="core")
