"""Armazenamento de anexos (contrato, termo aditivo etc. escaneados) em disco
local — `app/uploads/`, fora do controle de versão (ver .gitignore).

Em Docker Compose local, `backend/uploads/` já fica dentro do bind mount
`./backend:/app` do serviço `backend` (docker-compose.yml) — os arquivos
sobrevivem a reiniciar o container sem precisar de volume extra. Em deploy
sem disco persistente (Railway sem volume configurado), os arquivos NÃO
sobrevivem a um redeploy — ver nota no README.
"""

import re
import uuid
from pathlib import Path

DIRETORIO_UPLOADS = Path(__file__).resolve().parent.parent / "uploads"

_CARACTERES_INVALIDOS = re.compile(r"[^A-Za-z0-9._-]+")

# Extensões aceitas — os tipos de documento de apoio administrativo de um
# processo (contrato, termo aditivo, parecer, nota fiscal digitalizada).
EXTENSOES_PERMITIDAS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".jpg",
    ".jpeg",
    ".png",
}


class ExtensaoNaoPermitida(Exception):
    """Extensão do arquivo não está na lista de tipos aceitos."""


def _sanitizar_nome(nome: str) -> str:
    """Descarta qualquer caminho embutido no nome (ex.: "../../etc/passwd")
    e troca caracteres fora de um conjunto seguro por "_" — o nome original
    ainda fica guardado no banco para exibição, isto aqui é só o nome no
    disco."""
    nome = Path(nome).name
    nome = _CARACTERES_INVALIDOS.sub("_", nome)
    return nome[-150:] or "arquivo"


def salvar_anexo(instrumento_id: uuid.UUID, nome_original: str, conteudo: bytes) -> tuple[str, str]:
    """Grava o arquivo em disco e devolve (caminho_relativo, nome_sanitizado).
    `caminho_relativo` é o que fica salvo no banco — nunca o caminho
    absoluto do servidor."""
    extensao = Path(nome_original).suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise ExtensaoNaoPermitida(
            f"Tipo de arquivo '{extensao or '(sem extensão)'}' não permitido. "
            f"Extensões aceitas: {', '.join(sorted(EXTENSOES_PERMITIDAS))}."
        )

    nome_sanitizado = _sanitizar_nome(nome_original)
    nome_no_disco = f"{uuid.uuid4()}_{nome_sanitizado}"
    diretorio = DIRETORIO_UPLOADS / "instrumentos" / str(instrumento_id)
    diretorio.mkdir(parents=True, exist_ok=True)
    (diretorio / nome_no_disco).write_bytes(conteudo)

    caminho_relativo = f"instrumentos/{instrumento_id}/{nome_no_disco}"
    return caminho_relativo, nome_sanitizado


def caminho_absoluto(caminho_relativo: str) -> Path:
    return DIRETORIO_UPLOADS / caminho_relativo


def remover_arquivo(caminho_relativo: str) -> None:
    caminho_absoluto(caminho_relativo).unlink(missing_ok=True)
