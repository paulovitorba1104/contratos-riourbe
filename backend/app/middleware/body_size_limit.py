from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class LimiteTamanhoCorpoMiddleware(BaseHTTPMiddleware):
    """Limite de tamanho de corpo de requisição no próprio backend (não só no proxy)."""

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self._max_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": "Corpo da requisição excede o tamanho máximo permitido."},
            )
        return await call_next(request)
