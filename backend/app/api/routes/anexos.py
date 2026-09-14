import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, get_current_user
from app.db.session import get_db
from app.models.instrumento_processual import AnexoInstrumento
from app.models.usuario import Usuario
from app.services import armazenamento
from app.services.auditoria import registrar_log

router = APIRouter(prefix="/anexos", tags=["anexos"])


@router.get("/{anexo_id}")
def baixar_anexo(
    anexo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> FileResponse:
    anexo = db.get(AnexoInstrumento, anexo_id)
    if anexo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")

    caminho = armazenamento.caminho_absoluto(anexo.caminho_relativo)
    if not caminho.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Arquivo não encontrado no servidor — pode ter sido perdido num redeploy sem "
                "disco persistente."
            ),
        )
    # "inline" (não "attachment"): o pedido é visualização rápida — o
    # navegador abre o PDF/imagem direto, sem forçar download.
    return FileResponse(
        caminho, media_type=anexo.tipo_mime, filename=anexo.nome_arquivo, content_disposition_type="inline"
    )


@router.delete("/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_anexo(
    anexo_id: uuid.UUID,
    db: Session = Depends(get_db),
    # Exclusão definitiva — restrita a administrador, mesmo padrão de todo
    # cadastro do sistema.
    usuario: Usuario = Depends(exigir_administrador),
) -> None:
    anexo = db.get(AnexoInstrumento, anexo_id)
    if anexo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")

    armazenamento.remover_arquivo(anexo.caminho_relativo)
    registrar_log(
        db,
        usuario_id=usuario.id,
        acao="excluir_anexo_instrumento",
        entidade="instrumento_processual",
        entidade_id=str(anexo.instrumento_id),
        detalhes={"nome_arquivo": anexo.nome_arquivo},
    )
    db.delete(anexo)
    db.commit()
