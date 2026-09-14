"""Setor responsável pelo faturamento e valor pago anterior ao sistema

Revision ID: 0009_setor_e_valor_historico
Revises: 0008_excecao_teto_vigencia
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0009_setor_e_valor_historico"
down_revision: Union[str, None] = "0008_excecao_teto_vigencia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("faturamento_gerido_pela_gct", sa.Boolean(), nullable=False, server_default=sa.true()),
        schema="contratos",
    )
    op.add_column(
        "contratos",
        sa.Column("setor_responsavel_faturamento", sa.String(length=100), nullable=True),
        schema="contratos",
    )
    # server_default só para preencher as linhas existentes na criação da
    # coluna — nenhum default fica de pé na tabela depois disso, cada
    # contrato deve passar explicitamente pela regra do schema Pydantic.
    op.alter_column("contratos", "faturamento_gerido_pela_gct", schema="contratos", server_default=None)

    op.add_column(
        "contratos",
        sa.Column("valor_pago_anterior_sistema", sa.Numeric(16, 2), nullable=False, server_default="0"),
        schema="contratos",
    )
    op.alter_column("contratos", "valor_pago_anterior_sistema", schema="contratos", server_default=None)

    # Backfill: até aqui, `valor_pago` de todo contrato era ou 100% lançado à
    # mão (nenhuma fatura no sistema ainda), ou 100% recalculado como a soma
    # das faturas pagas (o antigo `_sincronizar_valor_pago` sobrescrevia,
    # nunca somava). Preserva o total de hoje sem duplicar: joga tudo para
    # `valor_pago_anterior_sistema` e, só para quem já tem fatura paga no
    # sistema, subtrai a parte que já é coberta por ela — o resto (se
    # houver) é o que foi pago antes/fora do sistema.
    op.execute("UPDATE contratos.contratos SET valor_pago_anterior_sistema = valor_pago")
    op.execute(
        """
        UPDATE contratos.contratos c
        SET valor_pago_anterior_sistema = GREATEST(c.valor_pago_anterior_sistema - sub.total_pago, 0)
        FROM (
            SELECT f.contrato_id, SUM(f.valor_bruto - COALESCE(g.total_glosa, 0)) AS total_pago
            FROM faturas.faturas f
            LEFT JOIN (
                SELECT fatura_id, SUM(valor) AS total_glosa
                FROM faturas.glosas
                GROUP BY fatura_id
            ) g ON g.fatura_id = f.id
            WHERE f.status = 'paga'
            GROUP BY f.contrato_id
        ) sub
        WHERE sub.contrato_id = c.id
        """
    )


def downgrade() -> None:
    op.drop_column("contratos", "valor_pago_anterior_sistema", schema="contratos")
    op.drop_column("contratos", "setor_responsavel_faturamento", schema="contratos")
    op.drop_column("contratos", "faturamento_gerido_pela_gct", schema="contratos")
