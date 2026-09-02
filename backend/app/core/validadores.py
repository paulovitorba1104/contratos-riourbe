"""Validadores de documentos reaproveitáveis entre módulos (fora do escopo
de autenticação — ver app/core/security.py para CPF usado no login)."""

import re


def normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


def normalizar_matricula(matricula: str) -> str:
    return re.sub(r"\D", "", matricula)


def matricula_valida(matricula: str) -> bool:
    """Formato padrão da matrícula: 00/000.000-0 — 9 dígitos."""
    return len(normalizar_matricula(matricula)) == 9


def cnpj_valido(cnpj: str) -> bool:
    digitos = normalizar_cnpj(cnpj)
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False

    def _dv(parcial: str, pesos: list[int]) -> str:
        soma = sum(int(d) * peso for d, peso in zip(parcial, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    dv1 = _dv(digitos[:12], pesos1)
    dv2 = _dv(digitos[:12] + dv1, pesos2)
    return digitos[-2:] == dv1 + dv2
