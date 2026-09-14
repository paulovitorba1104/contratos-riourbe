from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.tempo import hoje_brasilia

UTC = ZoneInfo("UTC")
BRASILIA = ZoneInfo("America/Sao_Paulo")


def test_hoje_brasilia_nao_adianta_um_dia_quando_utc_ja_virou_amanha():
    """21h-23h59 em Brasília é 00h-02h59 em UTC do dia seguinte — a janela
    exata em que um `date.today()` ingênuo rodando num servidor em UTC (caso
    comum de container sem fuso configurado) contaria o prazo um dia
    adiantado. 23h30 de 31/12 em Brasília é 02h30 de 01/01 em UTC."""
    instante = datetime(2026, 1, 1, 2, 30, tzinfo=UTC)
    assert hoje_brasilia(instante) == date(2025, 12, 31)


def test_hoje_brasilia_bate_com_a_data_local_fora_da_janela_critica():
    instante = datetime(2026, 6, 12, 15, 0, tzinfo=UTC)  # meio-dia em Brasília
    assert hoje_brasilia(instante) == date(2026, 6, 12)


def test_hoje_brasilia_aceita_instante_em_qualquer_fuso():
    instante = datetime(2026, 1, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))  # UTC-5
    # 01/01 01h30 em Nova York (UTC-5) = 01/01 03h30 UTC = 01/01 00h30 em Brasília (UTC-3)
    assert hoje_brasilia(instante) == date(2026, 1, 1)


def test_hoje_brasilia_sem_argumento_devolve_um_date():
    assert isinstance(hoje_brasilia(), date)
