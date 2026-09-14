from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class LimiteTamanhoCorpoMiddleware(BaseHTTPMiddleware):
    """Limite de tamanho de corpo de requisição no próprio backend (não só no
    proxy). Upload de anexo (contrato/aditivo escaneado) tem limite maior —
    identificado pelo trecho "/anexos" no caminho, não por rota exata, para
    não precisar listar cada rota de upload aqui."""

    def __init__(self, app, max_bytes: int, max_bytes_upload: int | None = None) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes
        self._max_bytes_upload = max_bytes_upload or max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        limite = self._max_bytes_upload if "/anexos" in request.url.path else self._max_bytes
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > limite:
            return JSONResponse(
                status_code=413,
                content={"detail": "Corpo da requisição excede o tamanho máximo permitido."},
            )
        return await call_next(request)
