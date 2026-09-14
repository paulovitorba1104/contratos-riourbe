"""Data de "hoje" para contagem de prazo — sempre em horário de Brasília,
independente de em que fuso o servidor está rodando.

Containers costumam vir configurados em UTC por padrão (é o caso da imagem
`python:3.12-slim` usada no Dockerfile, sem nenhum ajuste de fuso). Usar
`date.today()` puro nesse caso conta o dia errado durante as 3 horas diárias
em que UTC já virou o dia seguinte mas ainda é o dia anterior em Brasília
(21h-23h59, horário de Brasília) — um contrato podia aparecer "vencido" ou
mudar de faixa de alerta (6/3/1 mês) até 3 horas antes da hora certa.

Resolvido calculando o "hoje" explicitamente no fuso de Brasília, em vez de
depender da configuração do sistema operacional do servidor — assim o
resultado é o mesmo não importa onde o processo rode.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def hoje_brasilia(agora: datetime | None = None) -> date:
    """Data corrente em Brasília — usar em todo lugar que hoje calcula prazo,
    vencimento ou alerta (nunca `date.today()` puro nesses casos).

    `agora` é para teste (um instante ciente de fuso horário, de qualquer
    fuso); sem passar nada, usa o instante atual."""
    agora = agora or datetime.now(FUSO_BRASILIA)
    return agora.astimezone(FUSO_BRASILIA).date()
