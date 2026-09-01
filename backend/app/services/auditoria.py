import uuid

from sqlalchemy.orm import Session

from app.models.log_auditoria import LogAuditoria


def registrar_log(
    db: Session,
    *,
    usuario_id: uuid.UUID | None,
    acao: str,
    entidade: str,
    entidade_id: str | None = None,
    detalhes: dict | None = None,
) -> None:
    log = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
    )
    db.add(log)
