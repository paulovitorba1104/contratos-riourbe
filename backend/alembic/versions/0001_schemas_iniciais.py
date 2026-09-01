"""Schemas iniciais dos domínios + tabelas core (usuarios, log_auditoria)

Revision ID: 0001_schemas_iniciais
Revises:
Create Date: 2026-09-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_schemas_iniciais"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMAS = [
    "core",
    "contratos",
    "faturas",
    "licitacao",
    "compras",
    "almoxarifado",
    "fiscalizacao",
    "tarefas",
]


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    papel_usuario = postgresql.ENUM("administrador", "operador", name="papel_usuario", schema="core")
    papel_usuario.create(op.get_bind(), checkfirst=True)

    # create_type=False: o tipo já foi criado explicitamente acima.
    papel_usuario_coluna = postgresql.ENUM(
        "administrador", "operador", name="papel_usuario", schema="core", create_type=False
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("matricula", sa.String(length=30), nullable=True),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("papel", papel_usuario_coluna, nullable=False, server_default="operador"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sessoes_validas_apos", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("matricula", name="uq_core_usuarios_matricula"),
        sa.UniqueConstraint("cpf", name="uq_core_usuarios_cpf"),
        sa.UniqueConstraint("email", name="uq_core_usuarios_email"),
        schema="core",
    )

    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("acao", sa.String(length=100), nullable=False),
        sa.Column("entidade", sa.String(length=100), nullable=False),
        sa.Column("entidade_id", sa.String(length=100), nullable=True),
        sa.Column("detalhes", postgresql.JSONB(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["core.usuarios.id"], name="fk_log_auditoria_usuario", ondelete="SET NULL"
        ),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("log_auditoria", schema="core")
    op.drop_table("usuarios", schema="core")

    postgresql.ENUM(name="papel_usuario", schema="core").drop(op.get_bind())

    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
