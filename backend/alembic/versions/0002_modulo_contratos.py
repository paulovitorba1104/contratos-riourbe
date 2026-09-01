"""Módulo Contratos (Fase 1): fornecedores, contratos, instrumentos processuais,
modelos RIPM, atas de registro de preço

Revision ID: 0002_modulo_contratos
Revises: 0001_schemas_iniciais
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_modulo_contratos"
down_revision: Union[str, None] = "0001_schemas_iniciais"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _criar_enum(nome: str, valores: list[str], schema: str) -> postgresql.ENUM:
    tipo = postgresql.ENUM(*valores, name=nome, schema=schema)
    tipo.create(op.get_bind())
    return postgresql.ENUM(*valores, name=nome, schema=schema, create_type=False)


def upgrade() -> None:
    # --- core.fornecedores ---------------------------------------------
    op.create_table(
        "fornecedores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("razao_social", sa.String(length=255), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cnpj", name="uq_core_fornecedores_cnpj"),
        schema="core",
    )

    # --- contratos.modelos_ripm ------------------------------------------
    op.create_table(
        "modelos_ripm",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("itens_checklist", postgresql.JSONB(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_contratos_modelos_ripm_codigo"),
        schema="contratos",
    )

    # --- contratos.contratos ---------------------------------------------
    forma_contratacao = _criar_enum(
        "forma_contratacao", ["pregao_eletronico", "dispensa", "inexigibilidade"], "contratos"
    )
    status_contrato = _criar_enum("status_contrato", ["vigente", "suspenso", "encerrado"], "contratos")

    op.create_table(
        "contratos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("processo_sei", sa.String(length=50), nullable=False),
        sa.Column("tipo_servico", sa.String(length=200), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=False),
        sa.Column("fornecedor_id", sa.Uuid(), nullable=False),
        sa.Column("forma_contratacao", forma_contratacao, nullable=False),
        sa.Column("status", status_contrato, nullable=False, server_default="vigente"),
        sa.Column("data_assinatura_original", sa.Date(), nullable=False),
        sa.Column("valor_inicial", sa.Numeric(16, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("nota_reserva", sa.String(length=50), nullable=True),
        sa.Column("nota_empenho", sa.String(length=50), nullable=True),
        sa.Column("pt", sa.String(length=50), nullable=True),
        sa.Column("nd", sa.String(length=50), nullable=True),
        sa.Column("fr", sa.String(length=50), nullable=True),
        sa.Column("tipo_patrimonial", sa.String(length=100), nullable=True),
        sa.Column("item_patrimonial", sa.String(length=100), nullable=True),
        sa.Column("codigo_ccon", sa.String(length=50), nullable=True),
        sa.Column("data_inicio_garantia", sa.Date(), nullable=True),
        sa.Column("data_fim_garantia", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"], ["core.fornecedores.id"], name="fk_contratos_fornecedor"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_contratos_status", "contratos", ["status"], schema="contratos"
    )
    op.create_index(
        "ix_contratos_contratos_fornecedor_id", "contratos", ["fornecedor_id"], schema="contratos"
    )

    # --- contratos.contrato_fiscais ---------------------------------------
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

    # --- contratos.instrumentos_processuais -------------------------------
    tipo_instrumento = _criar_enum(
        "tipo_instrumento",
        [
            "origem",
            "prorrogacao",
            "acrescimo_valor",
            "supressao_valor",
            "alteracao_qualitativa",
            "reequilibrio",
            "apostilamento",
            "suspensao",
            "rescisao_extincao",
        ],
        "contratos",
    )
    fundamentacao_lei = _criar_enum("fundamentacao_lei", ["lei_13303_16", "lei_14133_21"], "contratos")
    sub_status_instrumento = _criar_enum(
        "sub_status_instrumento",
        ["elaboracao", "parecer_juridico", "assinatura", "publicado"],
        "contratos",
    )

    op.create_table(
        "instrumentos_processuais",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contrato_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", tipo_instrumento, nullable=False),
        sa.Column("modelo_ripm_id", sa.Uuid(), nullable=False),
        sa.Column("fundamentacao_lei", fundamentacao_lei, nullable=False),
        sa.Column("fundamentacao_artigo", sa.String(length=100), nullable=False),
        sa.Column(
            "sub_status", sub_status_instrumento, nullable=False, server_default="elaboracao"
        ),
        sa.Column("numero_documento_sei", sa.String(length=50), nullable=True),
        sa.Column("data_inicio_vigencia", sa.Date(), nullable=True),
        sa.Column("data_fim_vigencia", sa.Date(), nullable=True),
        sa.Column("valor_delta", sa.Numeric(16, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contrato_id"],
            ["contratos.contratos.id"],
            name="fk_instrumentos_contrato",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["modelo_ripm_id"], ["contratos.modelos_ripm.id"], name="fk_instrumentos_modelo_ripm"
        ),
        schema="contratos",
    )
    op.create_index(
        "ix_contratos_instrumentos_contrato_id",
        "instrumentos_processuais",
        ["contrato_id"],
        schema="contratos",
    )

    # --- contratos.atas_registro_preco -------------------------------------
    op.create_table(
        "atas_registro_preco",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("orgao", sa.String(length=255), nullable=False),
        sa.Column("numero_ata", sa.String(length=50), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=False),
        sa.Column("disponivel_para_adesao", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="contratos",
    )


def downgrade() -> None:
    op.drop_table("atas_registro_preco", schema="contratos")
    op.drop_table("instrumentos_processuais", schema="contratos")
    op.drop_table("contrato_fiscais", schema="contratos")
    op.drop_table("contratos", schema="contratos")
    op.drop_table("modelos_ripm", schema="contratos")
    op.drop_table("fornecedores", schema="core")

    for nome in (
        "sub_status_instrumento",
        "fundamentacao_lei",
        "tipo_instrumento",
        "status_contrato",
        "forma_contratacao",
    ):
        postgresql.ENUM(name=nome, schema="contratos").drop(op.get_bind())
