"""Rate limiting anti-força-bruta em 3 camadas (ip / conta / global).

Implementação em memória de processo — adequada para uma única instância de
backend (MVP em Railway). Se o backend passar a rodar em múltiplas
instâncias, migrar para um contador compartilhado (ex. Redis).

Ver seção 13 do plano de desenvolvimento (Rate limiting e anti-força-bruta).
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Janela:
    eventos: list[float] = field(default_factory=list)


class LimitadorTentativas:
    def __init__(self) -> None:
        self._janelas: dict[str, _Janela] = {}
        self._lock = threading.Lock()

    def _janela_de(self, chave: str) -> _Janela:
        janela = self._janelas.get(chave)
        if janela is None:
            janela = _Janela()
            self._janelas[chave] = janela
        return janela

    def registrar_falha(self, chave: str, janela_segundos: int) -> int:
        agora = time.time()
        with self._lock:
            janela = self._janela_de(chave)
            janela.eventos = [t for t in janela.eventos if agora - t < janela_segundos]
            janela.eventos.append(agora)
            return len(janela.eventos)

    def contagem_atual(self, chave: str, janela_segundos: int) -> int:
        agora = time.time()
        with self._lock:
            janela = self._janelas.get(chave)
            if janela is None:
                return 0
            janela.eventos = [t for t in janela.eventos if agora - t < janela_segundos]
            return len(janela.eventos)

    def limpar(self, chave: str) -> None:
        with self._lock:
            self._janelas.pop(chave, None)


# Limites por camada: (janela em segundos, máximo de falhas na janela)
LIMITE_IP = (15 * 60, 10)
LIMITE_CONTA = (15 * 60, 5)
LIMITE_GLOBAL = (15 * 60, 60)

_limitador = LimitadorTentativas()


class LoginBloqueado(Exception):
    def __init__(self, camada: str):
        self.camada = camada
        super().__init__(f"Muitas tentativas de login ({camada}).")


def verificar_bloqueio_login(ip: str, identificador: str) -> None:
    janela_ip, max_ip = LIMITE_IP
    janela_conta, max_conta = LIMITE_CONTA
    janela_global, max_global = LIMITE_GLOBAL

    if _limitador.contagem_atual("global:login", janela_global) >= max_global:
        raise LoginBloqueado("global")
    if _limitador.contagem_atual(f"ip:{ip}", janela_ip) >= max_ip:
        raise LoginBloqueado("ip")
    if _limitador.contagem_atual(f"conta:{identificador}", janela_conta) >= max_conta:
        raise LoginBloqueado("conta")


def registrar_falha_login(ip: str, identificador: str) -> None:
    _limitador.registrar_falha(f"ip:{ip}", LIMITE_IP[0])
    _limitador.registrar_falha(f"conta:{identificador}", LIMITE_CONTA[0])
    # O contador global nunca é limpo em caso de sucesso — apenas expira pela janela.
    _limitador.registrar_falha("global:login", LIMITE_GLOBAL[0])


def limpar_falhas_login(ip: str, identificador: str) -> None:
    """Em sucesso, limpa só as chaves de IP e conta — o contador global nunca é limpo."""
    _limitador.limpar(f"ip:{ip}")
    _limitador.limpar(f"conta:{identificador}")
